"""
MVP6.3 - Modèles Pydantic INPUT pour validation structures SQL

Validation des structures JSON générées par le LLM avant construction SQL.
"""

from pydantic import BaseModel
from typing import List, Optional, Union


class SQLCondition(BaseModel):
    """Modèle pour un élément de la liste 'conditions' (WHERE clause)."""
    
    column: str
    operator: str  # =, >, <, >=, <=, LIKE
    value: Union[str, int, float]


class SQLOrderBy(BaseModel):
    """Modèle pour un élément de la liste 'order_by' (ORDER BY clause)."""
    
    column: str
    direction: str = "ASC"  # ASC ou DESC, défaut: ASC (convention SQL)


class SQLQueryInput(BaseModel):
    """
    Modèle principal pour la structure SQL complète.
    
    Valide la structure JSON générée par le LLM avant construction de la requête SQL.
    Toutes les conditions sont reliées par AND (simplification MVP6).
    """
    
    table: str = "player_stats"  # Table unique dans MVP6
    columns: List[str]
    conditions: Optional[List[SQLCondition]] = []
    order_by: Optional[List[SQLOrderBy]] = []
    limit: Optional[int] = None


# ============================================================================
# Tests unitaires
# ============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("Tests de validation Pydantic")
    print("=" * 60)
    
    # Test 1: Structure complète valide
    print("\n--- Test 1: Structure complète ---")
    data1 = {
        "table": "player_stats",
        "columns": ["player", "pts"],
        "conditions": [{"column": "gp", "operator": ">=", "value": 50}],
        "order_by": [{"column": "pts", "direction": "DESC"}],
        "limit": 1
    }
    try:
        validated = SQLQueryInput(**data1)
        print(f"✅ Validé: {validated.table}, {len(validated.columns)} colonnes")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 2: Structure minimale (champs optionnels absents)
    print("\n--- Test 2: Structure minimale ---")
    data2 = {
        "columns": ["player", "team"]
    }
    try:
        validated = SQLQueryInput(**data2)
        print(f"✅ Validé: table='{validated.table}' (défaut)")
        print(f"   Conditions: {validated.conditions} (défaut)")
        print(f"   Order by: {validated.order_by} (défaut)")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 3: Validation échouée (champ obligatoire manquant)
    print("\n--- Test 3: Champ obligatoire manquant ---")
    data3 = {
        "table": "player_stats"
        # Manque "columns" (obligatoire)
    }
    try:
        validated = SQLQueryInput(**data3)
        print(f"✅ Validé")
    except Exception as e:
        print(f"❌ Erreur attendue: {type(e).__name__}")
    
    # Test 4: Validation échouée (mauvais type)
    print("\n--- Test 4: Mauvais type de données ---")
    data4 = {
        "columns": "player",  # String au lieu de List[str]
    }
    try:
        validated = SQLQueryInput(**data4)
        print(f"✅ Validé")
    except Exception as e:
        print(f"❌ Erreur attendue: {type(e).__name__}")
    
    print("\n" + "=" * 60)