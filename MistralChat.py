# MistralChat.py (version RAG avec logging complet)
import streamlit as st
import os
import logging
from mistralai import Mistral
from dotenv import load_dotenv
from utils.logger import setup_logger, log_timer_start, log_timer_end, log_retrieval, log_generation
from rag.routeur import route_question

setup_logger()

# --- Importations depuis vos modules ---
try:
    from utils.config import (
        MISTRAL_API_KEY, MODEL_NAME, SEARCH_K,
        APP_TITLE, NAME
    )
    from rag.vector_store import VectorStoreManager
except ImportError as e:
    st.error(f"Erreur d'importation: {e}. Vérifiez la structure de vos dossiers et les fichiers dans 'utils'.")
    st.stop()

# --- Configuration de l'API Mistral ---
api_key = MISTRAL_API_KEY
model = MODEL_NAME

if not api_key:
    st.error("Erreur : Clé API Mistral non trouvée (MISTRAL_API_KEY). Veuillez la définir dans le fichier .env.")
    st.stop()

try:
    client = Mistral(api_key=api_key)
    logging.info("Client Mistral initialisé.")
except Exception as e:
    st.error(f"Erreur lors de l'initialisation du client Mistral : {e}")
    logging.exception("Erreur initialisation client Mistral")
    st.stop()

# --- Chargement du Vector Store (mis en cache) ---
@st.cache_resource
def get_vector_store_manager():
    logging.info("Tentative de chargement du VectorStoreManager...")
    try:
        manager = VectorStoreManager()
        if manager.index is None or not manager.document_chunks:
            st.error("L'index vectoriel ou les chunks n'ont pas pu être chargés.")
            st.warning("Assurez-vous d'avoir exécuté 'python indexer.py' après avoir placé vos fichiers dans le dossier 'inputs'.")
            logging.error("Index Faiss ou chunks non trouvés/chargés par VectorStoreManager.")
            return None
        logging.info(f"VectorStoreManager chargé avec succès ({manager.index.ntotal} vecteurs).")
        return manager
    except FileNotFoundError:
         st.error("Fichiers d'index ou de chunks non trouvés.")
         st.warning("Veuillez exécuter 'python indexer.py' pour créer la base de connaissances.")
         logging.error("FileNotFoundError lors de l'init de VectorStoreManager.")
         return None
    except Exception as e:
        st.error(f"Erreur inattendue lors du chargement du VectorStoreManager: {e}")
        logging.exception("Erreur chargement VectorStoreManager")
        return None

vector_store_manager = get_vector_store_manager()

# --- Prompt Système pour RAG ---
SYSTEM_PROMPT = f"""Tu es 'NBA Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.

---
{{context_str}}
---

QUESTION DU FAN:
{{question}}

RÉPONSE DE L'ANALYSTE NBA:"""

# --- Initialisation de l'historique de conversation ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Bonjour ! Je suis votre analyste IA pour la {NAME}. Posez-moi vos questions sur les équipes, les joueurs ou les statistiques, et je vous répondrai en me basant sur les données les plus récentes."}]

# --- Fonctions ---
def generer_reponse(prompt_messages: list[dict]) -> str:
    """Envoie le prompt à l'API Mistral"""
    if not prompt_messages:
         logging.warning("Tentative de génération de réponse avec un prompt vide.")
         return "Je ne peux pas traiter une demande vide."
    try:
        logging.info(f"Appel à l'API Mistral modèle '{model}' avec {len(prompt_messages)} message(s).")
        
        response = client.chat.complete(
            model=model,
            messages=prompt_messages,
            temperature=0.1,
        )
        
        if response.choices and len(response.choices) > 0:
            logging.info("Réponse reçue de l'API Mistral.")
            return response.choices[0].message.content
        else:
            logging.warning("L'API n'a pas retourné de choix valide.")
            return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."
            
    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API Mistral: {e}")
        logging.exception("Erreur API Mistral pendant client.chat")
        return "Je suis désolé, une erreur technique m'empêche de répondre. Veuillez réessayer plus tard."

# --- Interface Utilisateur Streamlit ---
st.title(APP_TITLE)
st.caption(f"Assistant virtuel pour {NAME} | Modèle: {model}")

# Affichage des messages de l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Zone de saisie utilisateur
if prompt := st.chat_input(f"Posez votre question sur la {NAME}..."):
    
    # LOG1 : Démarrage du timer
    temps_debut = log_timer_start()
    
    # 1. Ajouter et afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. Vérifier si le Vector Store est disponible
    if vector_store_manager is None:
        st.error("Le service de recherche de connaissances n'est pas disponible.")
        logging.error("VectorStoreManager non disponible pour la recherche.")
        st.stop()

    # 3. NOUVEAU : Appel du routeur intelligent
    logging.info(f"Appel du routeur pour la question: '{prompt}'")
    routing_result = route_question(prompt, vector_store=vector_store_manager)
    
    # 4. Traitement selon la route détectée
    response_content = None
    
    # CAS 1 : SQL ou MIXTE → Réponse directe du routeur
    if routing_result["route"] in ["SQL", "MIXTE"]:
        logging.info(f"Route {routing_result['route']} détectée, réponse du routeur")
        
        if routing_result["error"]:
            response_content = f"Erreur : {routing_result['error']}"
            logging.error(f"Erreur route {routing_result['route']}: {routing_result['error']}")
        else:
            response_content = routing_result["response"]
            
        # LOG : Pas de prompt FAISS, on log directement
        log_generation(prompt, "Route SQL/MIXTE - Pas de prompt FAISS", response_content)
    
    # CAS 2 : FAISS ou FALLBACK → Utiliser la logique FAISS existante
    elif routing_result["route"] in ["FAISS", "FAISS_FALLBACK"]:
        logging.info(f"Route {routing_result['route']} détectée, utilisation logique FAISS")
        
        # Rechercher le contexte dans le Vector Store (CODE EXISTANT)
        try:
            logging.info(f"Recherche de contexte pour la question: '{prompt}' avec k={SEARCH_K}")
            search_results = vector_store_manager.search(prompt, k=SEARCH_K)
            
            # LOG2 : Logger les chunks retournés
            log_retrieval(search_results, SEARCH_K)
            
        except Exception as e:
            st.error(f"Une erreur est survenue lors de la recherche d'informations pertinentes: {e}")
            logging.exception(f"Erreur pendant vector_store_manager.search pour la query: {prompt}")
            search_results = []

        # Formater le contexte pour le prompt LLM (CODE EXISTANT)
        context_str = "\n\n---\n\n".join([
            f"Source: {res['metadata'].get('source', 'Inconnue')} (Score: {res['score']:.1f}%)\nContenu: {res['text']}"
            for res in search_results
        ])

        if not search_results:
            context_str = "Aucune information pertinente trouvée dans la base de connaissances pour cette question."
            logging.warning(f"Aucun contexte trouvé pour la query: {prompt}")

        # Construire le prompt final (CODE EXISTANT)
        final_prompt_for_llm = SYSTEM_PROMPT.format(context_str=context_str, question=prompt)
        messages_for_api = [{"role": "user", "content": final_prompt_for_llm}]

        # Générer la réponse (CODE EXISTANT)
        response_content = generer_reponse(messages_for_api)
        
        # LOG : Logger question, prompt et réponse (CODE EXISTANT)
        log_generation(prompt, final_prompt_for_llm, response_content)
    
    else:
        # Route inconnue
        response_content = "Erreur : route inconnue détectée."
        logging.error(f"Route inconnue: {routing_result['route']}")

    # 5. Afficher la réponse (COMMUN À TOUS LES CAS)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.text("...")
        message_placeholder.write(response_content)

    # 6. Ajouter la réponse à l'historique
    st.session_state.messages.append({"role": "assistant", "content": response_content})
    
    # LOG5 : Fin du timer
    duree = log_timer_end(temps_debut)
    logging.info(f"\n{'='*50}")
    logging.info(f"⏱️ TEMPS TOTAL: {duree}s")
    logging.info(f"{'='*50}\n")

# Pied de page
st.markdown("---")
st.caption("Powered by Mistral AI & Faiss | Data-driven NBA Insights")