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
    temp_db.save_race_result("Alice", "OPEN", 25.5, 500.0)
    
    # Check participant table
    stats = temp_db.get_participant_stats("Alice")
    assert len(stats) == 1
    assert stats[0]["race_time"] == 25.5
    assert stats[0]["race_distance"] == 500.0
    assert stats[0]["category"] == "OPEN"

def test_suggestions(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5, 500.0)
    temp_db.save_race_result("Bob", "OPEN", 22.1, 500.0)
    
    suggestions = temp_db.get_name_suggestions("Ali")
    assert "Alice" in suggestions
    assert "Bob" not in suggestions

def test_highscores_filtering(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5, 500.0)
    temp_db.save_race_result("Bob", "WTNB", 22.1, 1000.0)
    
    # Filter by category
    open_scores = temp_db.get_highscores(category="OPEN")
    assert len(open_scores) == 1
    assert open_scores[0]["name"] == "Alice"
    
    wtnb_scores = temp_db.get_highscores(category="WTNB")
    assert len(wtnb_scores) == 1
    assert wtnb_scores[0]["name"] == "Bob"
    
    # Sort by avg speed (Bob is 1000/22.1 = 45.2 m/s, Alice is 500/25.5 = 19.6 m/s)
    all_scores = temp_db.get_highscores()
    assert len(all_scores) == 2
    assert all_scores[0]["name"] == "Bob"

def test_delete_participant(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5, 500.0)
    temp_db.delete_participant("Alice")
    stats = temp_db.get_participant_stats("Alice")
    assert len(stats) == 0

def test_clear_all_data(temp_db):
    temp_db.save_race_result("Alice", "OPEN", 25.5, 500.0)
    temp_db.save_race_result("Bob", "WTNB", 22.1, 500.0)
    temp_db.clear_all_data()
    
    assert len(temp_db.get_highscores()) == 0
    assert len(temp_db.get_name_suggestions("A")) == 0
