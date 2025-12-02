"""
MVP6.3 - Génération de structures SQL depuis questions utilisateur
BLOC 2 : Prompt enrichi avec schéma DB + codes équipes + exemples
"""

import os
import json
import logging
import pandas as pd
from pathlib import Path
from mistralai import Mistral

# Ajouter le répertoire parent au path pour pouvoir importer utils
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import configuration
from utils.config import MISTRAL_API_KEY, MODEL_NAME

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation client Mistral
client = Mistral(api_key=MISTRAL_API_KEY)

# ============================================================================
# CHARGEMENT SCHÉMA DB AU DÉMARRAGE DU MODULE
# ============================================================================

def load_database_schema():
    """
    Charge le schéma de la base de données depuis dictionnaire_enrichi.csv.
    
    Returns:
        str: Schéma formaté pour le prompt LLM
    """
    dict_path = project_root / "data" / "config" / "dictionnaire_enrichi.csv"
    
    if not dict_path.exists():
        logger.error(f"Dictionnaire introuvable: {dict_path}")
        return "Schéma non disponible"
    
    df = pd.read_csv(dict_path)
    
    # Formater le schéma: nom_colonne_sql (TYPE) : définition
    schema_lines = []
    for _, row in df.iterrows():
        col_sql = row['nom_colonne_sql']
        col_type = row['type_sql'].upper()
        definition = row['definition']
        schema_lines.append(f"  - {col_sql} ({col_type}): {definition}")
    
    return "\n".join(schema_lines)

# Charger le schéma une seule fois au démarrage
DATABASE_SCHEMA = load_database_schema()

# ============================================================================
# DICTIONNAIRE DES ÉQUIPES NBA (hardcodé pour projet soutenance)
# ============================================================================

NBA_TEAMS = {
    "ATL": "Atlanta Hawks",
    "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "LA Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards"
}

def format_teams_for_prompt():
    """Formate le dictionnaire des équipes pour le prompt."""
    teams_list = [f"{code}: {name}" for code, name in NBA_TEAMS.items()]
    return "\n  ".join(teams_list)

# ============================================================================
# FONCTION PRINCIPALE DE GÉNÉRATION
# ============================================================================

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
    
    # Prompt enrichi avec schéma DB + équipes + exemples
    prompt = f"""Tu es un assistant qui génère des structures SQL au format JSON pour interroger une base de données PostgreSQL.

**BASE DE DONNÉES :**

Table: player_stats (569 joueurs NBA)
Colonnes disponibles:
{DATABASE_SCHEMA}

**CODES ÉQUIPES NBA :**
  {format_teams_for_prompt()}

**INSTRUCTIONS :**
1. Analyse la question de l'utilisateur
2. Identifie les colonnes nécessaires (utilise EXACTEMENT les noms ci-dessus)
3. Détermine les conditions WHERE si besoin
4. Détermine l'ordre de tri si besoin
5. Génère une structure JSON UNIQUEMENT (pas de texte autour)

**STRUCTURE JSON ATTENDUE :**
{{
  "table": "player_stats",
  "columns": ["colonne1", "colonne2"],
  "conditions": [{{"column": "col", "operator": ">=", "value": 50}}],
  "order_by": [{{"column": "col", "direction": "DESC"}}],
  "limit": 1
}}

**EXEMPLES :**

Exemple 1 - Meilleur joueur sur une statistique:
Question: "Who has the best PPG?"
{{
  "table": "player_stats",
  "columns": ["player_name", "ppg"],
  "conditions": [],
  "order_by": [{{"column": "ppg", "direction": "DESC"}}],
  "limit": 1
}}

Exemple 2 - Statistique d'un joueur spécifique:
Question: "What is LeBron James' FT%?"
{{
  "table": "player_stats",
  "columns": ["player_name", "ft_pct"],
  "conditions": [{{"column": "player_name", "operator": "LIKE", "value": "%LeBron%"}}],
  "order_by": [],
  "limit": null
}}

Exemple 3 - Top N joueurs:
Question: "Who are the top 3 players by total points?"
{{
  "table": "player_stats",
  "columns": ["player_name", "pts"],
  "conditions": [],
  "order_by": [{{"column": "pts", "direction": "DESC"}}],
  "limit": 3
}}

**QUESTION DE L'UTILISATEUR :**
{question}

**GÉNÈRE UNIQUEMENT LE JSON (sans texte autour, sans balises markdown) :**"""

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


# ============================================================================
# TESTS BLOC 2
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Test BLOC 2 - Prompt enrichi avec schéma DB")
    print("=" * 60)
    
    # Afficher le schéma chargé (premiers 5 lignes pour vérification)
    print("\n📋 Schéma DB chargé (aperçu):")
    schema_lines = DATABASE_SCHEMA.split("\n")[:5]
    for line in schema_lines:
        print(line)
    print(f"  ... et {len(DATABASE_SCHEMA.split(chr(10))) - 5} autres colonnes")
    
    print(f"\n🏀 Équipes NBA chargées: {len(NBA_TEAMS)} équipes")
    print(f"  Exemple: LAL = {NBA_TEAMS['LAL']}")
    
    print("\n" + "=" * 60)
    print("Tests de génération:")
    print("=" * 60)
    
    # Test 1: Meilleur PPG (devrait maintenant utiliser "ppg" et "player_stats")
    print("\n--- Test 1: Best PPG ---")
    question1 = "Who has the best PPG?"
    result1 = generate_sql_structure(question1)
    print(f"Question: {question1}")
    print(f"Table: {result1['table']}")
    print(f"Colonnes: {result1['columns']}")
    print(f"Tri: {result1['order_by']}")
    
    # Test 2: Joueur d'une équipe (devrait utiliser le code équipe)
    print("\n--- Test 2: Players from Lakers ---")
    question2 = "Who plays for the Lakers?"
    result2 = generate_sql_structure(question2)
    print(f"Question: {question2}")
    print(f"Conditions: {result2['conditions']}")
    
    # Test 3: Top 3
    print("\n--- Test 3: Top 3 players by points ---")
    question3 = "Who are the top 3 players by total points?"
    result3 = generate_sql_structure(question3)
    print(f"Question: {question3}")
    print(f"Colonnes: {result3['columns']}")
    print(f"Limit: {result3['limit']}")