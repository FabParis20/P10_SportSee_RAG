# scripts/test_classifier_on_dataset.py
"""
Test du classifier LLM sur le dataset d'évaluation (16 questions)
Calcule la précision et identifie les erreurs de classification
"""

import json
import logging
import sys
from pathlib import Path
from collections import defaultdict

# Ajouter le répertoire parent au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.classifier import classify_question

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chemin vers le dataset
DATASET_PATH = project_root / "data" / "evaluation" / "evaluation_dataset.json"

# Mapping type dataset → source attendue
TYPE_TO_SOURCE = {
    "reddit_only": "FAISS",
    "reddit_piege": "FAISS",
    "excel_only": "SQL",
    "excel_piege": "SQL",  # Sauf si stat inexistante
    "mixte": "MIXTE",
    "mixte_piege": "MIXTE"
}

# Questions pièges avec stats inexistantes (doivent aller vers FAISS)
STATS_INEXISTANTES = {
    7: "PER",  # Question 7: PER n'existe pas dans la DB
}


def load_dataset():
    """Charge le dataset d'évaluation"""
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['questions']


def evaluate_classification(question_data):
    """
    Évalue la classification d'une question
    
    Returns:
        dict avec résultat, attendu, correct, confiance
    """
    q_id = question_data['id']
    q_type = question_data['type']
    question_text = question_data['question']
    
    # Classification par le LLM
    result = classify_question(question_text)
    
    # Source attendue
    expected_source = TYPE_TO_SOURCE[q_type]
    
    # Exception pour stats inexistantes
    if q_id in STATS_INEXISTANTES:
        expected_source = "FAISS"
    
    # Vérifier si correct
    is_correct = (result['source'] == expected_source)
    
    return {
        'id': q_id,
        'type': q_type,
        'question': question_text[:80] + "..." if len(question_text) > 80 else question_text,
        'expected': expected_source,
        'predicted': result['source'],
        'correct': is_correct,
        'confiance': result['confiance'],
        'raison': result['raison']
    }


def main():
    """Test complet sur les 16 questions"""
    
    print("=" * 80)
    print("TEST CLASSIFIER SUR DATASET COMPLET (16 QUESTIONS)")
    print("=" * 80)
    
    # Charger dataset
    questions = load_dataset()
    print(f"\n✓ Dataset chargé: {len(questions)} questions\n")
    
    # Tester chaque question
    results = []
    stats_by_type = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    for i, q_data in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"Question {i}/{len(questions)} (ID: {q_data['id']}, Type: {q_data['type']})")
        print(f"{'='*80}")
        print(f"Q: {q_data['question'][:100]}...")
        
        # Classifier
        eval_result = evaluate_classification(q_data)
        results.append(eval_result)
        
        # Afficher résultat
        status = "✅ CORRECT" if eval_result['correct'] else "❌ ERREUR"
        print(f"\nAttendu: {eval_result['expected']}")
        print(f"Prédit:  {eval_result['predicted']} (confiance: {eval_result['confiance']})")
        print(f"Raison:  {eval_result['raison']}")
        print(f"\n{status}")
        
        # Stats par type
        q_type = q_data['type']
        stats_by_type[q_type]['total'] += 1
        if eval_result['correct']:
            stats_by_type[q_type]['correct'] += 1
    
    # Résumé global
    print(f"\n\n{'='*80}")
    print("RÉSUMÉ DES RÉSULTATS")
    print(f"{'='*80}\n")
    
    total_correct = sum(1 for r in results if r['correct'])
    total = len(results)
    precision = (total_correct / total) * 100
    
    print(f"Précision globale: {total_correct}/{total} ({precision:.1f}%)\n")
    
    # Stats par type
    print("Précision par type de question:")
    for q_type in sorted(stats_by_type.keys()):
        stats = stats_by_type[q_type]
        type_precision = (stats['correct'] / stats['total']) * 100
        print(f"  - {q_type:20s}: {stats['correct']}/{stats['total']} ({type_precision:.1f}%)")
    
    # Erreurs détaillées
    errors = [r for r in results if not r['correct']]
    if errors:
        print(f"\n\n❌ ERREURS DE CLASSIFICATION ({len(errors)}):")
        print("-" * 80)
        for err in errors:
            print(f"\nID {err['id']} ({err['type']}):")
            print(f"  Question: {err['question']}")
            print(f"  Attendu:  {err['expected']}")
            print(f"  Prédit:   {err['predicted']} (confiance: {err['confiance']})")
            print(f"  Raison:   {err['raison']}")
    
    # Objectif MVP6.2
    print(f"\n\n{'='*80}")
    if precision >= 80:
        print(f"✅ OBJECTIF ATTEINT: {precision:.1f}% ≥ 80%")
    else:
        print(f"⚠️  OBJECTIF NON ATTEINT: {precision:.1f}% < 80%")
    print(f"{'='*80}\n")
    
    # Sauvegarder résultats
    output_file = project_root / "data" / "evaluation" / "classifier_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'precision_globale': precision,
            'total_correct': total_correct,
            'total': total,
            'stats_by_type': dict(stats_by_type),
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Résultats sauvegardés dans: {output_file}\n")


if __name__ == "__main__":
    main()
