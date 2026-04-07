import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.bracket import BracketManager

def test_add_remove_participant():
    bm = BracketManager()
    bm.add_participant("OPEN", "Alice")
    bm.add_participant("OPEN", "Bob")
    assert "Alice" in bm.categories["OPEN"]["participants"]
    assert "Bob" in bm.categories["OPEN"]["participants"]
    
    bm.remove_participant("OPEN", "Alice")
    assert "Alice" not in bm.categories["OPEN"]["participants"]
    
def test_bracket_generation_even():
    bm = BracketManager()
    players = ["A", "B", "C", "D"]
    for p in players:
        bm.add_participant("OPEN", p)
        
    bm.generate_bracket("OPEN")
    bracket = bm.categories["OPEN"]["bracket"]
    
    assert len(bracket) == 2 # Round 1 (2 matches), Round 2 (1 match)
    assert len(bracket[0]) == 2
    assert len(bracket[1]) == 1
    
    # Check that next_match_id linkages exist
    m1, m2 = bracket[0]
    m3 = bracket[1][0]
    assert m1["next_match_id"] == m3["id"]
    assert m2["next_match_id"] == m3["id"]

def test_bracket_generation_odd():
    bm = BracketManager()
    players = ["A", "B", "C"]
    for p in players:
        bm.add_participant("OPEN", p)
        
    bm.generate_bracket("OPEN")
    bracket = bm.categories["OPEN"]["bracket"]
    
    assert len(bracket) == 2 # Round 1 (2 matches), Round 2 (1 match)
    assert len(bracket[0]) == 2
    
    # One match should have a BYE and an automatic winner
    r1_winners = [m["winner"] for m in bracket[0] if m["winner"] is not None]
    assert len(r1_winners) == 1
    assert r1_winners[0] in players # The person who got the BYE
