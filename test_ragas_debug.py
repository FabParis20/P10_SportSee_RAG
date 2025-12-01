"""
Script de test rapide pour débugger la structure RAGAS
Test avec seulement 2 questions pour aller vite
"""

import json
import sys
from pathlib import Path

# Ajouter le chemin du projet
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag.vector_store import VectorStoreManager
from utils.config import MISTRAL_API_KEY, MODEL_NAME, SEARCH_K
import requests

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings


def generate_answer_with_mistral(question: str, contexts: list) -> str:
    """Génère une réponse via Mistral"""
    context_text = "\n\n".join([f"Context {i+1}:\n{ctx}" for i, ctx in enumerate(contexts)])
    
    prompt = f"""Tu es un assistant expert en analyse de basketball NBA. 
Réponds à la question suivante en te basant UNIQUEMENT sur les informations fournies dans les contexts.

CONTEXTS:
{context_text}

QUESTION: {question}

RÉPONSE:"""

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
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"[ERREUR: {str(e)}]"


# 1. Charger seulement 2 questions du dataset
print("📂 Chargement de 2 questions de test...")
with open('data/evaluation/evaluation_dataset.json', 'r', encoding='utf-8') as f:
    full_dataset = json.load(f)

# Prendre les 2 premières questions
test_questions = full_dataset['questions'][:2]
print(f"✓ {len(test_questions)} questions chargées pour test")

# 2. Initialiser VectorStore
print("\n📊 Initialisation du VectorStore...")
vector_store = VectorStoreManager()
print("✓ VectorStore chargé")

# 3. Générer réponses et contexts
print("\n🔄 Génération des réponses...")
results = []

for q_data in test_questions:
    question = q_data['question']
    ground_truth = q_data['ground_truth']
    
    print(f"\nQ: {question[:60]}...")
    
    # Récupérer contexts
    search_results = vector_store.search(question, k=SEARCH_K)
    contexts = [result['text'] for result in search_results]
    print(f"✓ {len(contexts)} contexts")
    
    # Générer réponse
    answer = generate_answer_with_mistral(question, contexts)
    print(f"✓ Réponse générée ({len(answer)} chars)")
    
    results.append({
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "ground_truth": ground_truth
    })

# 4. Créer dataset RAGAS
print("\n📦 Préparation dataset RAGAS...")
ragas_dataset = Dataset.from_dict({
    "question": [r["question"] for r in results],
    "answer": [r["answer"] for r in results],
    "contexts": [r["contexts"] for r in results],
    "ground_truth": [r["ground_truth"] for r in results]
})

# 5. Évaluation RAGAS
print("\n🎯 Évaluation RAGAS (2 questions)...")

mistral_llm = ChatMistralAI(
    model=MODEL_NAME,
    mistral_api_key=MISTRAL_API_KEY,
    temperature=0.0
)

mistral_embeddings = MistralAIEmbeddings(
    model="mistral-embed",
    mistral_api_key=MISTRAL_API_KEY
)

evaluation_result = evaluate(
    ragas_dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ],
    llm=mistral_llm,
    embeddings=mistral_embeddings
)

# 6. DEBUG : Afficher la structure
print("\n" + "="*80)
print("🔍 DEBUG - STRUCTURE DE L'OBJET RAGAS")
print("="*80)
print(f"\n1️⃣ Type de l'objet :")
print(f"   {type(evaluation_result)}")

print(f"\n2️⃣ Contenu complet (print) :")
print(f"   {evaluation_result}")

print(f"\n3️⃣ Attributs disponibles (dir) :")
attributes = [attr for attr in dir(evaluation_result) if not attr.startswith('_')]
for attr in attributes:
    print(f"   - {attr}")

print(f"\n4️⃣ Test d'accès aux scores :")
try:
    print(f"   evaluation_result['faithfulness'] = {evaluation_result['faithfulness']}")
    print(f"   Type = {type(evaluation_result['faithfulness'])}")
except Exception as e:
    print(f"   ❌ Erreur avec ['faithfulness'] : {e}")

try:
    print(f"\n   evaluation_result.scores = {evaluation_result.scores}")
    print(f"   Type = {type(evaluation_result.scores)}")
except Exception as e:
    print(f"   ❌ Erreur avec .scores : {e}")

print(f"\n5️⃣ LA BONNE MÉTHODE - Accès aux scores moyens :")
try:
    scores_dict = evaluation_result.scores
    print(f"   Type: {type(scores_dict)}")
    print(f"   Contenu: {scores_dict}")
    print(f"\n   Faithfulness: {scores_dict['faithfulness']}")
    print(f"   Answer Relevancy: {scores_dict['answer_relevancy']}")
    print(f"   Context Precision: {scores_dict['context_precision']}")
    print(f"   Context Recall: {scores_dict['context_recall']}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

print("\n" + "="*80)
print("✅ Debug terminé !")
print("="*80)