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

def test_duplicate_participant():
    bm = BracketManager()
    error = bm.add_participant("OPEN", "Alice")
    assert error is None
    
    # Duplicate in same category
    error = bm.add_participant("OPEN", "Alice")
    assert "already registered" in error.lower()
    
    # Duplicate in different category
    error = bm.add_participant("WTNB", "Alice")
    assert "already registered" in error.lower()
    
    # Case sensitivity (if we want to enforce it, currently it is case sensitive by default 'Alice' != 'alice')
    # Let's check current behavior
    error = bm.add_participant("OPEN", "alice")
    assert error is None # 'alice' is different from 'Alice'
    
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

def test_manual_advance():
    bm = BracketManager()
    players = ["A", "B"]
    for p in players:
        bm.add_participant("OPEN", p)
    bm.generate_bracket("OPEN")
    
    bracket = bm.categories["OPEN"]["bracket"]
    match_id = bracket[0][0]["id"]
    
    # Manually advance A
    bm.manual_advance("OPEN", match_id, "A")
    
    assert bracket[0][0]["winner"] == "A"
    assert bracket[0][0]["_actual_winner"] is True
    
    # In this 2-player case, A should be champion
    assert bm.champions["OPEN"]["name"] == "A"

def test_tournament_concurrency_bug():
    """
    Tests Bug 1: Ensure that in a multi-round bracket, completing the first heat
    does NOT prematurely declare a champion, and the next active match is correctly
    queued for the remaining heat in Round 1.
    """
    bm = BracketManager()
    players = ["A", "B", "C", "D"]
    for p in players:
        bm.add_participant("OPEN", p)
    bm.generate_bracket("OPEN")
    
    # Verify initial state: Round 1 has 2 matches.
    bracket = bm.categories["OPEN"]["bracket"]
    assert len(bracket) == 2  # 2 rounds
    
    first_match = bm.active_match
    assert first_match is not None
    assert first_match["category"] == "OPEN"
    
    # Simulate finishing the first heat.
    # Player "A" wins the first match.
    bm.advance_winner("OPEN", first_match["id"], "A", winner_time=12.5)
    
    # BUG ASSERTION 1: The overall champion should NOT be set yet.
    assert bm.champions.get("OPEN") is None, "Champion was set prematurely after the first heat!"
    
    # BUG ASSERTION 2: The next active match should be the second heat in Round 1.
    next_match = bm.active_match
    assert next_match is not None, "Next active match was not queued."
    assert next_match["id"] != first_match["id"], "Active match did not advance."

def test_implicit_boolean_check_bug():
    """
    Tests Bug 4.4: Ensure that empty strings or '0' are treated as valid participant names 
    by explicit None checks rather than implicit truthiness checks.
    """
    bm = BracketManager()
    players = ["", "B", "C", "D"]
    for p in players:
        bm.add_participant("OPEN", p)
    bm.generate_bracket("OPEN")
    
    bracket = bm.categories["OPEN"]["bracket"]
    first_match = bracket[0][0]
    
    # Manually advance the empty string participant
    bm.advance_winner("OPEN", first_match["id"], "")
    
    # The winner should be propagated to the next round
    next_match_id = first_match["next_match_id"]
    next_match = None
    for m in bracket[1]:
        if m["id"] == next_match_id:
            next_match = m
            break
            
    assert next_match is not None
    # We should see "" propagated to p1 or p2 of the next match
    assert next_match["p1"] == "" or next_match["p2"] == "", f"Empty string winner was not propagated! Next match state: {next_match}"

def test_simultaneous_tournaments():
    """
    Tests Phase 1: Ensure that multiple categories can have active tournaments 
    simultaneously, and declaring a champion in one does not affect the other.
    """
    bm = BracketManager()
    
    # 1. Setup brackets for both categories
    bm.add_participant("OPEN", "O1")
    bm.add_participant("OPEN", "O2")
    bm.generate_bracket("OPEN")
    
    bm.add_participant("WTNB", "W1")
    bm.add_participant("WTNB", "W2")
    bm.generate_bracket("WTNB")
    
    # 2. Advance winner in OPEN to get a champion
    open_match = bm.categories["OPEN"]["bracket"][0][0]
    bm.advance_winner("OPEN", open_match["id"], "O1")
    
    # 3. Verify OPEN has a champion, but WTNB is still in bracket mode
    state = bm.get_state()
    assert state["champions"].get("OPEN") is not None
    assert state["champions"]["OPEN"]["name"] == "O1"
    
    # WTNB should still have no champion and its bracket should be visible/playable
    assert state["champions"].get("WTNB") is None
    
    # 4. Verify find_next_active_match correctly finds the match in WTNB 
    # if OPEN is finished.
    bm.active_category = "OPEN"
    bm.find_next_active_match()
    assert bm.active_match is not None
    assert bm.active_match["category"] == "WTNB"
    assert bm.active_match["p1"] in ["W1", "W2"]
    assert bm.active_match["p2"] in ["W1", "W2"]


