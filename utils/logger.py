# utils/logger.py
import logging
import time
from datetime import datetime
from utils.config import APPEND_LOGS

def setup_logger():
    """Initialise le système de logging pour le RAG"""
    
    # Déterminer le mode d'ouverture du fichier
    mode = 'a' if APPEND_LOGS else 'w'
    
    # Configurer le logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler('rag_debug.log', mode=mode, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Logger le démarrage
    logging.info(f"\n{'='*50}")
    logging.info(f"SESSION DÉMARRÉE : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"{'='*50}\n")

def log_timer_start():
    """Démarre le chronomètre - Retourne le timestamp de départ"""
    return time.time()

def log_timer_end(temps_debut):
    """Calcule et retourne la durée écoulée en secondes"""
    temps_fin = time.time()
    duree = temps_fin - temps_debut
    return round(duree, 2)

def log_retrieval(search_results, k):
    """
    LOG2 : Enregistre les chunks retournés par la recherche vectorielle
    
    Args:
        search_results: Liste des résultats de recherche
        k: Nombre de chunks demandés
    """
    logging.info(f"\n{'='*50}")
    logging.info(f"RECHERCHE VECTORIELLE (k={k})")
    logging.info(f"{'='*50}")
    
    if not search_results:
        logging.info("❌ AUCUN CHUNK TROUVÉ")
    else:
        logging.info(f"✅ {len(search_results)} CHUNKS RETOURNÉS:\n")
        for i, result in enumerate(search_results, 1):
            source = result['metadata'].get('source', 'Inconnue') 
            score = result['score']
            text = result['text'].replace('\x00', '').replace('\ufeff', '')
            text = text[:150] + "..." if len(text) > 150 else text
            
            logging.info(f"--- CHUNK {i} ---")
            logging.info(f"Source: {source}")
            logging.info(f"Score: {score:.2f}%")
            logging.info(f"Extrait: {text}")
            logging.info("")

def log_generation(question, prompt_complet, reponse):
    """
    LOG3 et LOG4 : Enregistre la question, le prompt et la réponse
    
    Args:
        question: Question originale de l'utilisateur
        prompt_complet: Prompt complet envoyé à Mistral
        reponse: Réponse générée par Mistral
    """
    question = question.replace('\x00', '')
    prompt_complet = prompt_complet.replace('\x00', '')
    reponse = reponse.replace('\x00', '')

    logging.info(f"\n{'='*50}")
    logging.info(f"QUESTION UTILISATEUR")
    logging.info(f"{'='*50}")
    logging.info(question)
    
    logging.info(f"\n{'='*50}")
    logging.info(f"PROMPT ENVOYÉ À MISTRAL")
    logging.info(f"{'='*50}")
    logging.info(prompt_complet)
    
    logging.info(f"\n{'='*50}")
    logging.info(f"RÉPONSE GÉNÉRÉE")
    logging.info(f"{'='*50}")
    logging.info(reponse)