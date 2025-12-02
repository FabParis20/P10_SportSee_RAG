"""
MVP6.3 - BLOC 4 : Construction de requêtes SQL depuis structures validées

Construit une requête SQL à partir d'une structure Pydantic validée.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from schemas.sql_models import SQLQueryInput, SQLCondition, SQLOrderBy


def build_sql_query(validated_structure: SQLQueryInput) -> str:
    """
    Construit une requête SQL depuis une structure Pydantic validée.
    
    Args:
        validated_structure: Structure SQL validée par Pydantic
        
    Returns:
        str: Requête SQL complète
        
    Example:
        >>> structure = SQLQueryInput(
        ...     columns=["player", "pts"],
        ...     conditions=[SQLCondition(column="gp", operator=">=", value=50)],
        ...     order_by=[SQLOrderBy(column="pts", direction="DESC")],
        ...     limit=1
        ... )
        >>> query = build_sql_query(structure)
        >>> print(query)
        SELECT player, pts FROM player_stats WHERE gp >= 50 ORDER BY pts DESC LIMIT 1
    """
    
    # 1. SELECT + colonnes
    columns_str = ", ".join(validated_structure.columns)
    query = f"SELECT {columns_str}"
    
    # 2. FROM + table
    query += f" FROM {validated_structure.table}"
    
    # 3. WHERE + conditions (si présentes)
    if validated_structure.conditions:
        conditions_clauses = []
        for condition in validated_structure.conditions:
            # Échapper les valeurs string avec quotes
            if isinstance(condition.value, str):
                value = f"'{condition.value}'"
            else:
                value = str(condition.value)
            
            conditions_clauses.append(f"{condition.column} {condition.operator} {value}")
        
        # Relier toutes les conditions par AND (simplification MVP6)
        query += " WHERE " + " AND ".join(conditions_clauses)
    
    # 4. ORDER BY (si présent)
    if validated_structure.order_by:
        order_clauses = []
        for order in validated_structure.order_by:
            order_clauses.append(f"{order.column} {order.direction}")
        
        query += " ORDER BY " + ", ".join(order_clauses)
    
    # 5. LIMIT (si présent)
    if validated_structure.limit is not None:
        query += f" LIMIT {validated_structure.limit}"
    
    return query


# ============================================================================
# Tests unitaires
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Tests de construction SQL")
    print("=" * 70)
    
    # Test 1: Requête complète (tous les champs)
    print("\n--- Test 1: Requête complète ---")
    structure1 = SQLQueryInput(
        columns=["player", "pts"],
        conditions=[SQLCondition(column="gp", operator=">=", value=50)],
        order_by=[SQLOrderBy(column="pts", direction="DESC")],
        limit=1
    )
    sql1 = build_sql_query(structure1)
    print(f"Structure: {structure1.model_dump()}")
    print(f"SQL: {sql1}")
    
    # Test 2: Sans conditions (ORDER BY + LIMIT uniquement)
    print("\n--- Test 2: Sans conditions ---")
    structure2 = SQLQueryInput(
        columns=["player", "team", "pts"],
        order_by=[SQLOrderBy(column="pts", direction="DESC")],
        limit=3
    )
    sql2 = build_sql_query(structure2)
    print(f"SQL: {sql2}")
    
    # Test 3: Juste SELECT (pas de WHERE, ORDER BY, LIMIT)
    print("\n--- Test 3: Requête minimale ---")
    structure3 = SQLQueryInput(
        columns=["player", "team"]
    )
    sql3 = build_sql_query(structure3)
    print(f"SQL: {sql3}")
    
    # Test 4: Multiples conditions et ORDER BY
    print("\n--- Test 4: Multiples conditions et tris ---")
    structure4 = SQLQueryInput(
        columns=["player", "pts", "ppg"],
        conditions=[
            SQLCondition(column="gp", operator=">=", value=50),
            SQLCondition(column="team", operator="=", value="LAL")
        ],
        order_by=[
            SQLOrderBy(column="pts", direction="DESC"),
            SQLOrderBy(column="player", direction="ASC")
        ]
    )
    sql4 = build_sql_query(structure4)
    print(f"SQL: {sql4}")
    
    # Test 5: Opérateur LIKE
    print("\n--- Test 5: Opérateur LIKE ---")
    structure5 = SQLQueryInput(
        columns=["player", "pts"],
        conditions=[SQLCondition(column="player", operator="LIKE", value="%LeBron%")]
    )
    sql5 = build_sql_query(structure5)
    print(f"SQL: {sql5}")
    
    print("\n" + "=" * 70)
    print("✅ Tous les tests de construction SQL terminés")
    print("=" * 70)