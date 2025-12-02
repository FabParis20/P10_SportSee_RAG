"""
MVP6.3 - Génération de structures SQL depuis questions utilisateur
"""

import os
import json
import logging
import sys
from pathlib import Path
from mistralai import Mistral

# Ajouter le répertoire parent au path pour pouvoir importer utils
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import configuration
from utils.config import MISTRAL_API_KEY, MODEL_NAME

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation client Mistral
client = Mistral(api_key=MISTRAL_API_KEY)


def generate_sql_structure(question: str) -> dict:
    """
    Génère une structure SQL (format JSON) depuis une question utilisateur.
    
    Args:
        question: Question de l'utilisateur (déjà classifiée comme SQL)
        
    Returns:
        dict: Structure SQL au format JSON
        {
            "table": str,
            "columns": list[str],
            "conditions": list[dict],
            "order_by": list[dict],
            "limit": int
        }
    """
    logger.info(f"Génération structure SQL pour: '{question}'")
    
    # Prompt simple pour BLOC 1 (sera enrichi au BLOC 2)
    prompt = f"""Tu es un assistant qui génère des structures SQL au format JSON.

Question: {question}

Génère une structure JSON avec les champs suivants:
- table: nom de la table
- columns: liste des colonnes à sélectionner
- conditions: liste des conditions WHERE (vide si aucune)
- order_by: liste des tris (vide si aucun)
- limit: nombre de résultats (null si pas de limite)

Réponds UNIQUEMENT avec le JSON, sans texte autour."""

    # Appel API Mistral
    response = client.chat.complete(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Extraction du contenu
    response_text = response.choices[0].message.content
    
    # Nettoyage balises markdown si présentes
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    
    # Parse JSON
    sql_structure = json.loads(response_text)
    
    logger.info(f"Structure générée: {sql_structure}")
    
    return sql_structure


# Tests BLOC 1
if __name__ == "__main__":
    print("=" * 60)
    print("Test BLOC 1 - Génération structure SQL")
    print("=" * 60)
    
    # Test 1: Question simple
    question = "Who has the best PPG?"
    result = generate_sql_structure(question)
    print(f"\nQuestion: {question}")
    print(f"Résultat: {json.dumps(result, indent=2)}")