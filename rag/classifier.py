# rag/classifier.py
import json
import logging
import sys
import pandas as pd
from pathlib import Path

# Ajouter le répertoire parent au path pour pouvoir importer utils
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mistralai import Mistral
from utils.config import MISTRAL_API_KEY, MODEL_NAME

import logfire

# Configuration Logfire
logfire.configure()

logger = logging.getLogger(__name__)

# Chemin vers le dictionnaire des colonnes SQL
DICTIONNAIRE_PATH = project_root / "data" / "config" / "dictionnaire_enrichi.csv"

# Chemin vers le fichier de log des classifications
CLASSIFICATIONS_LOG = project_root / "logs" / "classifications.log"


def log_classification_to_file(question: str, result: dict):
    """
    Log la classification dans un fichier dédié pour analyse post-mortem
    
    Args:
        question: Question classifiée
        result: Résultat de la classification
    """
    try:
        # Créer le dossier logs s'il n'existe pas
        CLASSIFICATIONS_LOG.parent.mkdir(exist_ok=True)
        
        # Formater l'entrée de log
        log_entry = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "question": question,
            "source": result["source"],
            "type": result["type"],
            "confiance": result["confiance"],
            "raison": result["raison"]
        }
        
        # Écrire dans le fichier
        with open(CLASSIFICATIONS_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
    except Exception as e:
        logger.warning(f"Impossible de logger dans le fichier: {e}")


def load_database_schema() -> str:
    """
    Charge le dictionnaire des colonnes SQL et le formate pour le prompt.
    
    Returns:
        String formaté avec toutes les colonnes disponibles
    """
    try:
        df = pd.read_csv(DICTIONNAIRE_PATH)
        
        # Formater chaque ligne : nom_sql (définition)
        colonnes = []
        for _, row in df.iterrows():
            colonnes.append(f"- {row['nom_sql_normalise']}: {row['definition']}")
        
        schema_text = "\n".join(colonnes)
        return schema_text
        
    except Exception as e:
        logger.error(f"Erreur chargement dictionnaire: {e}")
        return "Erreur: impossible de charger le schéma de la base de données"

@logfire.instrument()
def classify_question(question: str) -> dict:
    """
    Classifie une question vers SQL, FAISS, ou MIXTE.
    
    Args:
        question: Question de l'utilisateur
        
    Returns:
        {
            "source": "SQL" | "FAISS" | "MIXTE",
            "type": str,
            "confiance": float,
            "raison": str
        }
    """
    try:
        logger.info(f"Classification de la question: '{question}'")
        
        # Charger le schéma de la base de données
        db_schema = load_database_schema()
        
        # Initialiser le client Mistral
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        # Construire le prompt de classification enrichi
        prompt = f"""Tu es un classificateur pour un système RAG NBA.

SOURCES DISPONIBLES:

1. PostgreSQL: Base de données avec statistiques de 569 joueurs NBA
   COLONNES DISPONIBLES (45 statistiques):
{db_schema}

2. FAISS: Discussions Reddit de fans et analystes NBA (opinions, analyses qualitatives)

RÈGLES DE CLASSIFICATION:
- Si la question porte sur des STATISTIQUES NUMÉRIQUES disponibles dans PostgreSQL → SQL
- Si la stat demandée N'EXISTE PAS dans PostgreSQL (ex: VORP) → FAISS  
- Si la question porte sur des OPINIONS, ANALYSES, ou DISCUSSIONS → FAISS
- Si la question nécessite à la fois STATS + OPINIONS → MIXTE

RÈGLES DE VÉRIFICATION DES STATISTIQUES (CRITIQUE):
1. Si la question mentionne explicitement un acronyme de stat (ex: PER, VORP, PPG), vérifier d'ABORD s'il existe EXACTEMENT dans les colonnes ci-dessus
2. Si l'acronyme n'existe PAS exactement → vérifier s'il pourrait être une faute de frappe évidente (ex: GPP → PPG, FT% → FG%)
3. Si ce n'est PAS une faute de frappe ET que la stat n'existe pas → router vers FAISS
4. ATTENTION : PER ≠ PIE (Player Efficiency Rating ≠ Player Impact Estimate - ce sont deux stats DIFFÉRENTES)
5. EN CAS DE DOUTE sur l'existence d'une stat → router vers FAISS (principe de précaution)

TÂCHE:
Classifie cette question vers SQL, FAISS, ou MIXTE.

QUESTION: {question}

RÉPONDS UNIQUEMENT avec ce JSON (rien d'autre):
{{
  "source": "SQL" ou "FAISS" ou "MIXTE",
  "type": "best_stat_player" ou "single_stat_value" ou "compare_players" ou "qualitative_analysis" ou "mixed_analysis",
  "confiance": 0.85,
  "raison": "explication courte"
}}"""

        # Appel API Mistral
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        # Extraire la réponse
        response_text = response.choices[0].message.content.strip()
        
        # Nettoyer les balises markdown si présentes
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
        
        # Parser le JSON
        result = json.loads(response_text)
        
        # Logging détaillé de la classification
        logger.info(f"Classification: {result['source']} (confiance: {result['confiance']})")
        logger.debug(f"  Type: {result['type']}")
        logger.debug(f"  Raison: {result['raison']}")
        logger.debug(f"  Question: {question[:100]}...")
        
        # Logger dans fichier dédié pour analyse
        log_classification_to_file(question, result)
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Erreur parsing JSON de classification: {e}")
        logger.error(f"Réponse reçue: {response_text}")
        # Fallback: retourner FAISS par défaut
        return {
            "source": "FAISS",
            "type": "qualitative_analysis",
            "confiance": 0.3,
            "raison": "Erreur de parsing - fallback vers FAISS"
        }
    
    except Exception as e:
        logger.exception(f"Erreur lors de la classification: {e}")
        # Fallback: retourner FAISS par défaut
        return {
            "source": "FAISS",
            "type": "qualitative_analysis",
            "confiance": 0.3,
            "raison": f"Erreur technique - fallback vers FAISS"
        }


if __name__ == "__main__":
    # Test rapide
    logging.basicConfig(level=logging.INFO)
    
    test_questions = [
        "Who has the best PPG?",
        "What do fans think of the Lakers?",
        "How is LeBron performing this season?",
        "What is LeBron's VORP?"  # VORP n'existe pas dans la DB
    ]
    
    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {q}")
        result = classify_question(q)
        print(f"Résultat: {json.dumps(result, indent=2, ensure_ascii=False)}")