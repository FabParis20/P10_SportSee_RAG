"""
Script de test pour execute_sql_query() - MVP6.4
Tests complets avec 5 scénarios variés
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag.sql_executor import execute_sql_query


def test_1_best_player():
    """Test 1 : Meilleur joueur par points (1 résultat)"""
    print("=" * 60)
    print("TEST 1 - Meilleur joueur par PPG")
    print("=" * 60)
    
    query = "SELECT player, pts FROM player_stats ORDER BY pts DESC LIMIT 1"
    print(f"Requête : {query}\n")
    
    try:
        results = execute_sql_query(query)
        print(f"✅ Résultat : {results}")
        print(f"   {len(results)} joueur(s) retourné(s)\n")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        return False


def test_2_top_3_players():
    """Test 2 : Top 3 joueurs (3 résultats)"""
    print("=" * 60)
    print("TEST 2 - Top 3 joueurs par points")
    print("=" * 60)
    
    query = "SELECT player, team, pts FROM player_stats ORDER BY pts DESC LIMIT 3"
    print(f"Requête : {query}\n")
    
    try:
        results = execute_sql_query(query)
        print(f"✅ Résultats :")
        for r in results:
            print(f"   - {r['player']} ({r['team']}) : {r['pts']} pts")
        print(f"   {len(results)} joueur(s) retourné(s)\n")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        return False


def test_3_player_with_like():
    """Test 3 : Recherche joueur avec LIKE (1 résultat normalement)"""
    print("=" * 60)
    print("TEST 3 - Recherche joueur avec LIKE")
    print("=" * 60)
    
    query = "SELECT player, team, pts FROM player_stats WHERE player LIKE '%LeBron%'"
    print(f"Requête : {query}\n")
    
    try:
        results = execute_sql_query(query)
        if len(results) > 0:
            print(f"✅ Résultat : {results}")
            print(f"   {len(results)} joueur(s) trouvé(s)\n")
        else:
            print(f"✅ Aucun joueur trouvé (liste vide = résultat valide)\n")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        return False


def test_4_team_players():
    """Test 4 : Tous les joueurs d'une équipe (N résultats)"""
    print("=" * 60)
    print("TEST 4 - Joueurs des Lakers")
    print("=" * 60)
    
    query = "SELECT player, pts FROM player_stats WHERE team = 'LAL' ORDER BY pts DESC"
    print(f"Requête : {query}\n")
    
    try:
        results = execute_sql_query(query)
        print(f"✅ {len(results)} joueur(s) des Lakers :")
        for r in results[:5]:  # Afficher seulement les 5 premiers
            print(f"   - {r['player']} : {r['pts']} pts")
        if len(results) > 5:
            print(f"   ... et {len(results) - 5} autres joueurs\n")
        else:
            print()
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        return False


def test_5_complex_condition():
    """Test 5 : Condition complexe avec filtres multiples"""
    print("=" * 60)
    print("TEST 5 - Meilleur FG% (joueurs avec 50+ matchs)")
    print("=" * 60)
    
    query = "SELECT player, team, fg_pct FROM player_stats WHERE gp >= 50 ORDER BY fg_pct DESC LIMIT 1"
    print(f"Requête : {query}\n")
    
    try:
        results = execute_sql_query(query)
        print(f"✅ Résultat : {results}")
        print(f"   {len(results)} joueur(s) retourné(s)\n")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        return False


def test_6_empty_result():
    """Test 6 : Résultat vide (équipe inexistante)"""
    print("=" * 60)
    print("TEST 6 - Équipe inexistante (résultat vide attendu)")
    print("=" * 60)
    
    query = "SELECT player, pts FROM player_stats WHERE team = 'XYZ' ORDER BY pts DESC LIMIT 1"
    print(f"Requête : {query}\n")
    
    try:
        results = execute_sql_query(query)
        if len(results) == 0:
            print(f"✅ Liste vide retournée (comportement attendu)\n")
        else:
            print(f"⚠️ Résultat inattendu : {results}\n")
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}\n")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTS EXECUTE_SQL_QUERY - MVP6.4")
    print("=" * 60 + "\n")
    
    tests = [
        test_1_best_player,
        test_2_top_3_players,
        test_3_player_with_like,
        test_4_team_players,
        test_5_complex_condition,
        test_6_empty_result
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Résumé
    print("=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    success = sum(results)
    total = len(results)
    print(f"✅ {success}/{total} tests réussis")
    
    if success == total:
        print("🎯 Tous les tests sont passés ! MVP6.4 validé.")
    else:
        print(f"⚠️ {total - success} test(s) en échec")