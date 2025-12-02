"""
MVP6.3 - BLOC 5 : Tests sur dataset complet + intégration pipeline

Pipeline complet : Question → JSON → Validation Pydantic → SQL
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import sys

# Ajouter racine projet au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.sql_generator import generate_sql_structure
from rag.sql_builder import build_sql_query
from schemas.sql_models import SQLQueryInput

# Configuration logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "sql_generations.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def test_sql_pipeline_on_dataset():
    """
    Teste le pipeline complet sur les questions SQL du dataset.
    
    Pipeline : Question → generate_sql_structure() → Pydantic validation → build_sql_query()
    """
    
    # Charger dataset
    dataset_path = project_root / "data" / "evaluation" / "evaluation_dataset.json"
    
    if not dataset_path.exists():
        logger.error(f"Dataset introuvable: {dataset_path}")
        return
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    # Filtrer questions SQL uniquement
    sql_questions = [
        q for q in dataset['questions'] 
        if q['type'] in ['excel_only', 'excel_piege', 'mixte', 'mixte_piege']
    ]
    
    logger.info(f"Dataset chargé: {len(sql_questions)} questions SQL à tester")
    
    results = []
    success_count = 0
    
    print("=" * 80)
    print(f"TESTS MVP6.3 - Pipeline SQL complet sur {len(sql_questions)} questions")
    print("=" * 80)
    
    for i, question_data in enumerate(sql_questions, 1):
        question_id = question_data['id']
        question = question_data['question']
        q_type = question_data['type']
        
        print(f"\n{'='*80}")
        print(f"Question {i}/{len(sql_questions)} - ID: {question_id} - Type: {q_type}")
        print(f"{'='*80}")
        print(f"Question: {question}")
        
        try:
            # ÉTAPE 1: Génération structure JSON par LLM
            logger.info(f"[{question_id}] Génération structure SQL...")
            json_structure = generate_sql_structure(question)
            print(f"\n✅ Structure JSON générée:")
            print(f"   Table: {json_structure['table']}")
            print(f"   Colonnes: {json_structure['columns']}")
            print(f"   Conditions: {json_structure.get('conditions', [])}")
            print(f"   Order by: {json_structure.get('order_by', [])}")
            print(f"   Limit: {json_structure.get('limit', None)}")
            
            # ÉTAPE 2: Validation Pydantic
            logger.info(f"[{question_id}] Validation Pydantic...")
            validated_structure = SQLQueryInput(**json_structure)
            print(f"\n✅ Validation Pydantic réussie")
            
            # ÉTAPE 3: Construction SQL
            logger.info(f"[{question_id}] Construction SQL...")
            sql_query = build_sql_query(validated_structure)
            print(f"\n✅ Requête SQL construite:")
            print(f"   {sql_query}")
            
            # Succès
            success_count += 1
            results.append({
                "id": question_id,
                "question": question,
                "type": q_type,
                "status": "success",
                "json_structure": json_structure,
                "sql_query": sql_query
            })
            
            logger.info(f"[{question_id}] ✅ Pipeline complet réussi")
            
        except Exception as e:
            # Échec
            error_msg = str(e)
            print(f"\n❌ ERREUR: {error_msg}")
            
            results.append({
                "id": question_id,
                "question": question,
                "type": q_type,
                "status": "error",
                "error": error_msg
            })
            
            logger.error(f"[{question_id}] ❌ Erreur: {error_msg}")
    
    # ========================================================================
    # RÉSULTATS GLOBAUX
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("RÉSULTATS GLOBAUX")
    print("=" * 80)
    
    success_rate = (success_count / len(sql_questions)) * 100
    print(f"\n✅ Succès: {success_count}/{len(sql_questions)} ({success_rate:.1f}%)")
    print(f"❌ Échecs: {len(sql_questions) - success_count}/{len(sql_questions)}")
    
    # Analyser erreurs par type
    errors_by_type = {}
    for result in results:
        if result['status'] == 'error':
            q_type = result['type']
            errors_by_type[q_type] = errors_by_type.get(q_type, 0) + 1
    
    if errors_by_type:
        print(f"\nErreurs par type de question:")
        for q_type, count in errors_by_type.items():
            print(f"  - {q_type}: {count} erreur(s)")
    
    # ========================================================================
    # SAUVEGARDE RÉSULTATS
    # ========================================================================
    
    output_path = project_root / "data" / "evaluation" / "sql_generation_results.json"
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(sql_questions),
        "success_count": success_count,
        "success_rate": success_rate,
        "results": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés: {output_path}")
    
    print("\n" + "=" * 80)
    print("✅ BLOC 5 TERMINÉ - Pipeline MVP6.3 validé")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    test_sql_pipeline_on_dataset()
