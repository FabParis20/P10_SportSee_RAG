"""
Script d'évaluation RAGAS pour le système RAG SportSee
MVP4 - P10_DSML

Ce script :
1. Charge le dataset de questions (evaluation_dataset.json)
2. Exécute chaque question via le système RAG (FAISS + Mistral)
3. Collecte les réponses et contexts
4. Évalue avec RAGAS (Faithfulness, Answer Relevancy, Context Precision, Context Recall)
5. Sauvegarde les résultats dans ragas_results.json

AMÉLIORATIONS :
- Sauvegarde intermédiaire après génération des réponses
- Sauvegarde intermédiaire après évaluation RAGAS
- Ajout du champ "type" dans detailed_results
- Prints de debug complets
"""

import json
import os
import sys
from pathlib import Path
import numpy as np

# Ajouter le chemin du projet pour importer les modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.vector_store import VectorStoreManager
from utils.config import MISTRAL_API_KEY, MODEL_NAME, SEARCH_K
from utils.logger import setup_logger, log_timer_start, log_timer_end
import requests
from tqdm import tqdm

# Importer RAGAS
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    )
    from ragas.run_config import RunConfig
    from datasets import Dataset
    from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
except ImportError:
    print("❌ ERREUR : RAGAS ou langchain-mistralai n'est pas installé.")
    print("Installez-les avec : uv add ragas langchain-mistralai")
    sys.exit(1)


def load_dataset(dataset_path: str) -> dict:
    """Charge le dataset de questions depuis le JSON"""
    print(f"📂 Chargement du dataset : {dataset_path}")
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✓ {len(data['questions'])} questions chargées")
    return data


def generate_answer_with_mistral(question: str, contexts: list) -> str:
    """
    Génère une réponse via l'API Mistral en utilisant les contexts
    
    Args:
        question: La question posée
        contexts: Liste des chunks récupérés par FAISS
        
    Returns:
        La réponse générée par Mistral
    """
    # Construire le prompt avec les contexts
    context_text = "\n\n".join([f"Context {i+1}:\n{ctx}" for i, ctx in enumerate(contexts)])
    
    prompt = f"""Tu es un assistant expert en analyse de basketball NBA. 
Réponds à la question suivante en te basant UNIQUEMENT sur les informations fournies dans les contexts.

CONTEXTS:
{context_text}

QUESTION: {question}

INSTRUCTIONS:
- Réponds de manière précise et factuelle
- Utilise UNIQUEMENT les informations des contexts fournis
- Si l'information n'est pas dans les contexts, dis-le clairement
- Ne pas inventer ou halluciner des informations
- Cite les sources (Reddit ou statistiques) quand c'est pertinent

RÉPONSE:"""

    # Appeler l'API Mistral
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        answer = result['choices'][0]['message']['content'].strip()
        return answer
    except Exception as e:
        print(f"❌ Erreur API Mistral : {e}")
        return f"[ERREUR: Impossible de générer la réponse - {str(e)}]"


def extract_score(value):
    """
    Extrait un score float depuis la valeur RAGAS.
    RAGAS retourne une liste de scores (un par question).
    On calcule la MOYENNE.
    """
    print(f"🔍 DEBUG extract_score() - Type: {type(value)}, Valeur: {value}")
    
    if isinstance(value, list):
        moyenne = float(np.mean(value))
        print(f"   → Liste détectée, calcul moyenne: {moyenne}")
        return moyenne
    
    score = float(value)
    print(f"   → Valeur simple: {score}")
    return score


def run_evaluation(dataset_path: str, output_path: str):
    """
    Exécute l'évaluation complète du système RAG avec RAGAS
    
    Args:
        dataset_path: Chemin vers evaluation_dataset.json
        output_path: Chemin pour sauvegarder ragas_results.json
    """
    print("="*80)
    print("🎯 ÉVALUATION RAGAS - MVP4")
    print("="*80)
    
    # Configurer le logger
    setup_logger()
    temps_debut = log_timer_start()
    
    # 1. Charger le dataset
    dataset = load_dataset(dataset_path)
    questions_data = dataset['questions']
    
    # 2. Initialiser le VectorStoreManager
    print("\n📊 Initialisation du VectorStore...")
    try:
        vector_store = VectorStoreManager()
        print("✓ VectorStore chargé avec succès")
    except Exception as e:
        print(f"❌ Erreur lors du chargement du VectorStore : {e}")
        print("Assurez-vous que l'index FAISS existe (exécutez indexer.py)")
        sys.exit(1)
    
    # 3. Générer les réponses et contexts pour chaque question
    print("\n🔄 Génération des réponses...")
    results = []
    
    for i, q_data in enumerate(tqdm(questions_data, desc="Questions traitées")):
        question = q_data['question']
        ground_truth = q_data['ground_truth']
        q_id = q_data['id']
        q_type = q_data['type']
        
        print(f"\n--- Question #{q_id} ({q_type}) ---")
        print(f"Q: {question[:80]}...")
        
        try:
            # Récupérer les contexts via FAISS
            search_results = vector_store.search(question, k=SEARCH_K)
            contexts = [result['text'] for result in search_results]
            
            print(f"✓ {len(contexts)} contexts récupérés")
            
            # Générer la réponse via Mistral
            answer = generate_answer_with_mistral(question, contexts)
            print(f"✓ Réponse générée ({len(answer)} caractères)")
            
            # Stocker pour RAGAS (AVEC LE TYPE!)
            results.append({
                "question_id": q_id,
                "question_type": q_type,  # ← CHAMP AJOUTÉ
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth
            })
            
        except Exception as e:
            print(f"❌ Erreur pour question #{q_id} : {e}")
            # Ajouter un résultat vide pour ne pas bloquer l'évaluation
            results.append({
                "question_id": q_id,
                "question_type": q_type,  # ← CHAMP AJOUTÉ ICI AUSSI
                "question": question,
                "answer": f"[ERREUR: {str(e)}]",
                "contexts": [""],
                "ground_truth": ground_truth
            })
    
    # 💾 SAUVEGARDE INTERMÉDIAIRE 1 : Réponses générées
    intermediate_file_1 = "data/evaluation/ragas_intermediate_answers.json"
    print(f"\n💾 Sauvegarde intermédiaire 1 : {intermediate_file_1}")
    with open(intermediate_file_1, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {"num_questions": len(questions_data), "timestamp": "2025-11-26"},
            "results": results
        }, f, indent=2, ensure_ascii=False)
    print("✓ Sauvegarde intermédiaire 1 OK - Les réponses sont sécurisées!")
      
    # 4. Convertir en Dataset RAGAS
    print("\n📦 Préparation du dataset RAGAS...")
    ragas_dataset = Dataset.from_dict({
        "question": [r["question"] for r in results],
        "answer": [r["answer"] for r in results],
        "contexts": [r["contexts"] for r in results],
        "ground_truth": [r["ground_truth"] for r in results]
    })
    
    # 5. Évaluer avec RAGAS
    print("\n🎯 Évaluation RAGAS en cours...")
    print("Métriques : Faithfulness, Answer Relevancy, Context Precision, Context Recall")

    try:
        # Configurer Mistral pour LLM ET embeddings
        mistral_llm = ChatMistralAI(
            model=MODEL_NAME,
            mistral_api_key=MISTRAL_API_KEY,
            temperature=0.0
        )
        
        mistral_embeddings = MistralAIEmbeddings(
            model="mistral-embed",
            mistral_api_key=MISTRAL_API_KEY
        )
        
        # 🔧 Configuration optimisée pour Mistral API (éviter 429 et TimeoutError)
        print("\n⚙️  Configuration RunConfig pour Mistral API:")
        print("   - timeout: 600s (10 minutes)")
        print("   - max_retries: 20")
        print("   - max_wait: 120s entre retries")
        print("   - max_workers: 2 (limite parallélisme pour éviter 429)")
        print("   - log_tenacity: True (logs des retries)")
        
        config_mistral_safe = RunConfig(
            timeout=600,           # 10 minutes au lieu de 3 (défaut 180s)
            max_retries=20,        # Plus de tentatives (défaut 10)
            max_wait=120,          # Attente plus longue entre retries (défaut 60s)
            max_workers=2,         # TRÈS IMPORTANT : 2 au lieu de 16 pour éviter rate limit!
            log_tenacity=True      # Logs pour voir les retries
        )
        
        print("\n🚀 Lancement de l'évaluation (peut prendre 15-30 minutes)...\n")
        
        evaluation_result = evaluate(
            ragas_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall
            ],
            llm=mistral_llm,
            embeddings=mistral_embeddings,
            run_config=config_mistral_safe  # ← Configuration optimale ajoutée
        )
        
        print("\n" + "="*80)
        print("📊 RÉSULTATS RAGAS BRUTS")
        print("="*80)
        print(evaluation_result)
        
        # 🔍 DEBUG COMPLET - Structure de l'objet
        print("\n" + "="*80)
        print("🔍 DEBUG - STRUCTURE COMPLÈTE DE L'OBJET RAGAS")
        print("="*80)
        print(f"\n1️⃣ Type de l'objet:")
        print(f"   {type(evaluation_result)}")
        
        print(f"\n2️⃣ Attributs disponibles (dir):")
        attrs = [attr for attr in dir(evaluation_result) if not attr.startswith('_')]
        for attr in attrs:
            print(f"   - {attr}")
        
        print(f"\n3️⃣ Accès aux scores individuels (listes):")
        print(f"   evaluation_result['faithfulness'] = {evaluation_result['faithfulness']}")
        print(f"   Type: {type(evaluation_result['faithfulness'])}")
        print(f"   Longueur: {len(evaluation_result['faithfulness'])}")
        
        print(f"\n   evaluation_result['answer_relevancy'] = {evaluation_result['answer_relevancy']}")
        print(f"   Type: {type(evaluation_result['answer_relevancy'])}")
        
        print(f"\n   evaluation_result['context_precision'] = {evaluation_result['context_precision']}")
        print(f"   Type: {type(evaluation_result['context_precision'])}")
        
        print(f"\n   evaluation_result['context_recall'] = {evaluation_result['context_recall']}")
        print(f"   Type: {type(evaluation_result['context_recall'])}")
        
        # 💾 SAUVEGARDE INTERMÉDIAIRE 2 : Résultat évaluation RAGAS brut
        intermediate_file_2 = "data/evaluation/ragas_intermediate_evaluation.json"
        print(f"\n💾 Sauvegarde intermédiaire 2 : {intermediate_file_2}")
        
        # Convertir en format sérialisable
        eval_data = {
            "faithfulness_scores": [float(x) for x in evaluation_result['faithfulness']],
            "answer_relevancy_scores": [float(x) for x in evaluation_result['answer_relevancy']],
            "context_precision_scores": [float(x) for x in evaluation_result['context_precision']],
            "context_recall_scores": [float(x) for x in evaluation_result['context_recall']]
        }
        
        with open(intermediate_file_2, 'w', encoding='utf-8') as f:
            json.dump(eval_data, f, indent=2)
        print("✓ Sauvegarde intermédiaire 2 OK - L'évaluation RAGAS est sécurisée!")

        # 6. Calculer scores moyens et sauvegarder résultats finaux
        print(f"\n💾 Sauvegarde des résultats finaux dans : {output_path}")
        
        print("\n4️⃣ Calcul des scores moyens avec extract_score():")
        
        faithfulness_mean = extract_score(evaluation_result["faithfulness"])
        answer_relevancy_mean = extract_score(evaluation_result["answer_relevancy"])
        context_precision_mean = extract_score(evaluation_result["context_precision"])
        context_recall_mean = extract_score(evaluation_result["context_recall"])
        
        # Convertir les résultats en dict pour JSON
        results_dict = {
            "metadata": {
                "dataset_path": dataset_path,
                "num_questions": len(questions_data),
                "model": MODEL_NAME,
                "search_k": SEARCH_K
            },
            "global_scores": {
                "faithfulness": faithfulness_mean,
                "answer_relevancy": answer_relevancy_mean,
                "context_precision": context_precision_mean,
                "context_recall": context_recall_mean
            },
            "detailed_results": results  # Contient déjà question_type
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        
        print("✓ Résultats finaux sauvegardés avec succès")
        
        # 7. Afficher un résumé
        print("\n" + "="*80)
        print("📈 RÉSUMÉ FINAL")
        print("="*80)
        print(f"Faithfulness      : {results_dict['global_scores']['faithfulness']:.3f}")
        print(f"Answer Relevancy  : {results_dict['global_scores']['answer_relevancy']:.3f}")
        print(f"Context Precision : {results_dict['global_scores']['context_precision']:.3f}")
        print(f"Context Recall    : {results_dict['global_scores']['context_recall']:.3f}")
        
        temps_total = log_timer_end(temps_debut)
        print(f"\n⏱️  Temps total : {temps_total:.2f} secondes")
        
        print("\n" + "="*80)
        print("✅ ÉVALUATION MVP4 TERMINÉE AVEC SUCCÈS !")
        print("="*80)
        print(f"\n📁 Fichiers générés:")
        print(f"   1. {intermediate_file_1} (réponses)")
        print(f"   2. {intermediate_file_2} (évaluation brute)")
        print(f"   3. {output_path} (résultats finaux)")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'évaluation RAGAS : {e}")
        print("Vérifiez que RAGAS est correctement installé et configuré")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Chemins des fichiers
    DATASET_PATH = "data/evaluation/evaluation_dataset.json"
    OUTPUT_PATH = "data/evaluation/ragas_results.json"
    
    # Vérifier que le dataset existe
    if not os.path.exists(DATASET_PATH):
        print(f"❌ ERREUR : Le fichier {DATASET_PATH} n'existe pas")
        print("Assurez-vous que evaluation_dataset.json est bien dans data/evaluation/")
        sys.exit(1)
    
    # Lancer l'évaluation
    run_evaluation(DATASET_PATH, OUTPUT_PATH)
