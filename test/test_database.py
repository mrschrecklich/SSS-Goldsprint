import pytest
import os
import sys
import sqlite3

# Add parent directory to sys.path to import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database import GoldsprintDB

@pytest.fixture
def temp_db():
    db_path = "test_goldsprint.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = GoldsprintDB(db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)

def test_save_and_retrieve_result(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5)
    
    # Check participant table
    stats = temp_db.get_participant_stats("Alice")
    assert len(stats) == 1
    assert stats[0]["race_time"] == 25.5
    assert stats[0]["category"] == "OPEN"

def test_suggestions(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5)
    temp_db.save_race_result("Bob", "OPEN", 22.1)
    
    suggestions = temp_db.get_name_suggestions("Ali")
    assert "Alice" in suggestions
    assert "Bob" not in suggestions

def test_highscores_filtering(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5)
    temp_db.save_race_result("Bob", "WTNB", 22.1)
    
    # Filter by category
    open_scores = temp_db.get_highscores(category="OPEN")
    assert len(open_scores) == 1
    assert open_scores[0]["name"] == "Alice"
    
    wtnb_scores = temp_db.get_highscores(category="WTNB")
    assert len(wtnb_scores) == 1
    assert wtnb_scores[0]["name"] == "Bob"
    
    # All scores
    all_scores = temp_db.get_highscores()
    assert len(all_scores) == 2
    assert all_scores[0]["name"] == "Bob" # Bob is faster
