"""
Module de formatage des résultats SQL en langage naturel.
MVP6.5 - Formatage LLM des réponses
"""

import logging
from mistralai import Mistral
from utils.config import MISTRAL_API_KEY, MODEL_NAME

import logfire

# Configuration Logfire
logfire.configure()

# Configuration du logger
logger = logging.getLogger(__name__)

# Initialisation client Mistral
client = Mistral(api_key=MISTRAL_API_KEY)

@logfire.instrument()
def format_sql_only(question: str, sql_results: list[dict]) -> str:
    """
    Formate les résultats SQL bruts en réponse naturelle.
    
    Args:
        question: Question originale de l'utilisateur
        sql_results: Résultats bruts PostgreSQL [{'col1': val1, ...}]
        
    Returns:
        str: Réponse formatée en langage naturel
    """
    logger.info(f"Formatage SQL only - Question: {question}")
    logger.info(f"Résultats SQL reçus: {len(sql_results)} lignes")
    
    # Construction du prompt
    prompt = f"""Tu es un assistant basketball NBA. Tu dois formuler une réponse naturelle à partir des données statistiques.

QUESTION DE L'UTILISATEUR :
{question}

DONNÉES STATISTIQUES (PostgreSQL) :
{sql_results}

INSTRUCTIONS :
1. Réponds dans la MÊME LANGUE que la question (français si question en français, anglais si question en anglais)
2. Formule une réponse complète et naturelle
3. Cite les statistiques précises (valeurs numériques)
4. Si liste vide [], dis "Aucun résultat trouvé"
5. Sois concis (2-3 phrases maximum)

RÉPONSE :"""

    try:
        # Appel LLM Mistral
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        
        formatted_response = response.choices[0].message.content.strip()
        logger.info(f"Réponse formatée (SQL only): {formatted_response[:100]}...")
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Erreur formatage SQL only: {e}")
        return f"Erreur lors du formatage de la réponse: {str(e)}"

@logfire.instrument()
def format_sql_mixte(question: str, sql_results: list[dict], faiss_context: str) -> str:
    """
    Fusionne résultats SQL + contexte FAISS en réponse naturelle.
    
    Args:
        question: Question originale de l'utilisateur
        sql_results: Résultats bruts PostgreSQL
        faiss_context: Contexte récupéré depuis discussions Reddit
        
    Returns:
        str: Réponse formatée fusionnant SQL + FAISS
    """
    logger.info(f"Formatage MIXTE - Question: {question}")
    logger.info(f"Résultats SQL: {len(sql_results)} lignes")
    logger.info(f"Contexte FAISS: {len(faiss_context)} caractères")
    
    # Construction du prompt
    prompt = f"""Tu es un assistant basketball NBA. Tu dois formuler une réponse complète en combinant données statistiques ET discussions Reddit.

QUESTION DE L'UTILISATEUR :
{question}

DONNÉES STATISTIQUES (PostgreSQL) :
{sql_results}

DISCUSSIONS REDDIT :
{faiss_context}

INSTRUCTIONS :
1. Réponds dans la MÊME LANGUE que la question
2. Commence par les statistiques précises (valeurs numériques)
3. Enrichis avec le contexte des discussions Reddit
4. Fusionne de manière naturelle (pas de séparation "stats:" puis "reddit:")
5. Sois concis (3-4 phrases maximum)

RÉPONSE :"""

    try:
        # Appel LLM Mistral
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        
        formatted_response = response.choices[0].message.content.strip()
        logger.info(f"Réponse formatée (MIXTE): {formatted_response[:100]}...")
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Erreur formatage MIXTE: {e}")
        return f"Erreur lors du formatage de la réponse: {str(e)}"