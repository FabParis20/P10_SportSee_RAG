"""
Module d'exécution de requêtes SQL dans PostgreSQL.
MVP6.4 - BLOC 1 : Fonction de base
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import logging
from sqlalchemy import create_engine, text
from utils.config import DATABASE_URL_POSTGRES as DATABASE_URL

# Configuration du logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler('logs/sql_executions.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def log_timer_start():
    """Démarre le chronomètre"""
    return time.time()


def log_timer_end(temps_debut):
    """Calcule la durée"""
    return round(time.time() - temps_debut, 2)


def execute_sql_query(query: str) -> list[dict]:
    """
    Exécute une requête SQL dans PostgreSQL et retourne les résultats.
    
    Args:
        query: Requête SQL à exécuter (format string)
        
    Returns:
        list[dict]: Résultats de la requête sous forme de liste de dictionnaires
        
    Raises:
        ConnectionError: Si la connexion à PostgreSQL échoue
        ValueError: Si la requête SQL est invalide
        
    Example:
        >>> query = "SELECT player, pts FROM player_stats ORDER BY pts DESC LIMIT 1"
        >>> results = execute_sql_query(query)
        >>> print(results)
        [{'player': 'Luka Doncic', 'pts': 28.4}]
    """
    logger.info(f"Exécution SQL : {query}")
    
    # Timer à l'EXTÉRIEUR des try/except (ne mesure que les succès)
    temps_debut = log_timer_start()
    
    # TRY 1 : Connexion à PostgreSQL
    try:
        engine = create_engine(DATABASE_URL)
        logger.debug("Connexion PostgreSQL établie")
    except Exception as e:
        logger.error(f"Erreur connexion PostgreSQL : {e}")
        raise ConnectionError(f"Impossible de se connecter à PostgreSQL : {e}")
    
    # TRY 2 : Exécution de la requête SQL
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            data = list(result.mappings())
            
            duree = log_timer_end(temps_debut)
            logger.info(f"Requête SQL réussie en {duree}s. {len(data)} résultat(s) retourné(s)")
            logger.debug(f"Premiers résultats : {data[:3] if len(data) > 0 else '[]'}")
            
            return data
            
    except Exception as e:
        logger.error(f"Erreur SQL syntax : {e}")
        raise ValueError(f"Requête SQL invalide : {e}")
    
    finally:
        # Fermeture de l'engine (libère les connexions)
        engine.dispose()
        logger.debug("Connexion PostgreSQL fermée")