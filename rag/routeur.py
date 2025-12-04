"""
Module de routage intelligent des questions.
MVP6.5 - Orchestration Classification → Exécution → Formatage
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from rag.classifier import classify_question
from rag.sql_generator import generate_sql_structure
from rag.sql_builder import build_sql_query
from rag.sql_executor import execute_sql_query
from rag.sql_formatter import format_sql_only, format_sql_mixte
from rag.vector_store import VectorStoreManager
from schemas.sql_models import SQLQueryInput
import logfire

# Configuration Logfire
logfire.configure()

# Configuration du logger
logger = logging.getLogger(__name__)

@logfire.instrument()
def route_question(question: str, vector_store: VectorStoreManager = None) -> dict:
    """
    Orchestre le traitement complet d'une question : classification → exécution → formatage.
    
    Gère 3 cas :
    - SQL only : Pipeline SQL complet → formatage
    - MIXTE : Pipeline SQL + FAISS → fusion
    - FAISS only : Retourne None (géré par MistralChat.py)
    
    Args:
        question: Question de l'utilisateur
        vector_store: Instance VectorStore pour recherche FAISS (nécessaire si MIXTE)
        
    Returns:
        dict: {
            "route": "SQL" | "MIXTE" | "FAISS",
            "response": str | None,
            "error": str | None
        }
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"ROUTEUR - Nouvelle question: {question}")
    logger.info(f"{'='*80}")
    
    try:
        # ÉTAPE 1 : Classification
        classification = classify_question(question)
        route = classification.get("source", "FAISS")
        logger.info(f"Route détectée: {route}")
        
        # ÉTAPE 2 : Traitement selon la route
        
        # CAS 1 : FAISS only (géré par MistralChat.py existant)
        if route == "FAISS":
            logger.info("Route FAISS → Retour à MistralChat.py")
            return {
                "route": "FAISS",
                "response": None,
                "error": None
            }
        
        # CAS 2 : SQL only
        elif route == "SQL":
            logger.info("Route SQL → Pipeline SQL complet")
            
            try:
                # Génération structure JSON
                json_structure = generate_sql_structure(question)
                logger.info(f"Structure JSON générée: {json_structure}")

                # Validation Pydantic INPUT
                from schemas.sql_models import SQLQueryInput
                validated_input = SQLQueryInput(**json_structure)
                logger.info("Structure validée par Pydantic")

                # Construction requête SQL
                sql_query = build_sql_query(validated_input)
                
                # Exécution PostgreSQL
                sql_results = execute_sql_query(sql_query)
                logger.info(f"Résultats SQL: {len(sql_results)} lignes")
                
                # Formatage réponse naturelle
                formatted_response = format_sql_only(question, sql_results)

                # ⚠️ Formatage du contexte
                formatted_contexts = [str(row) for row in sql_results]
                
                return {
                    "route": "SQL",
                    "response": formatted_response,
                    "contexts": formatted_contexts, # ⚠️
                    "error": None
                }
                
            except Exception as e:
                # FALLBACK SQL → FAISS
                logger.warning(f"Erreur pipeline SQL, fallback FAISS: {e}")
                
                if vector_store is None:
                    return {
                        "route": "SQL",
                        "response": None,
                        "error": f"Erreur SQL et pas de fallback FAISS disponible: {str(e)}"
                    }
                
                # Fallback vers FAISS
                logger.info("Tentative fallback FAISS...")
                return {
                    "route": "FAISS_FALLBACK",
                    "response": None,  # MistralChat.py gérera le FAISS
                    "error": None
                }
        
        # CAS 3 : MIXTE (SQL + FAISS)
        elif route == "MIXTE":
            logger.info("Route MIXTE → Pipeline SQL + FAISS")
            
            if vector_store is None:
                return {
                    "route": "MIXTE",
                    "response": None,
                    "error": "VectorStore non fourni pour route MIXTE"
                }
            
            try:
                # Partie SQL
                # Partie SQL
                json_structure = generate_sql_structure(question)
                
                # Validation Pydantic INPUT
                from schemas.sql_models import SQLQueryInput
                validated_input = SQLQueryInput(**json_structure)
                logger.info("Structure MIXTE validée par Pydantic")
                
                # Construction requête SQL
                sql_query = build_sql_query(validated_input)
                sql_results = execute_sql_query(sql_query)
                logger.info(f"Résultats SQL: {len(sql_results)} lignes")
                
                # Partie FAISS
                faiss_results = vector_store.search(question, k=3)
                faiss_context = "\n\n".join([chunk["text"] for chunk in faiss_results])
                logger.info(f"Contexte FAISS: {len(faiss_context)} caractères")
                
                # Fusion formatage
                formatted_response = format_sql_mixte(question, sql_results, faiss_context)

                # ⚠️ Formatage contexte mixte
                formatted_contexts = [str(row) for row in sql_results] + [chunk["text"] for chunk in faiss_results]
                
                return {
                    "route": "MIXTE",
                    "response": formatted_response,
                    "contexts": formatted_contexts, # ⚠️
                    "error": None
                }
                
            except Exception as e:
                logger.error(f"Erreur route MIXTE: {e}")
                return {
                    "route": "MIXTE",
                    "response": None,
                    "error": f"Erreur route MIXTE: {str(e)}"
                }
        
        else:
            # Route inconnue
            logger.warning(f"Route inconnue: {route}, fallback FAISS")
            return {
                "route": "FAISS",
                "response": None,
                "error": None
            }
            
    except Exception as e:
        logger.error(f"Erreur critique routeur: {e}")
        return {
            "route": "ERROR",
            "response": None,
            "error": f"Erreur critique: {str(e)}"
        }