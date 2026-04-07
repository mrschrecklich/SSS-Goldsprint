import sys
import os
import pytest
import time

# Add parent directory to sys.path to import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.engine import GoldsprintEngine

def test_race_logic():
    engine = GoldsprintEngine()
    engine.target_dist = 10
    engine.circumference = 2.0
    engine.is_racing = True
    engine.race_start_time = time.time()
    
    # P1 at 60 RPM = 1 rev/sec = 2m/s. In 3 seconds = 6m.
    error = engine.update_tick(60, 0, 3)
    assert error is None
    assert engine.p1["dist"] == 6
    assert engine.winner is None
    
    # Another 3 seconds = 12m total. Should win (at 10m).
    # We also give P2 some speed so they finish too, which triggers is_racing = False
    error = engine.update_tick(60, 60, 3)
    assert error is None
    assert engine.p1["dist"] == 10
    assert engine.winner == "Player 1"
    
    # Another 3 seconds for P2 to finish
    engine.update_tick(0, 60, 3)
    assert engine.is_racing is False

def test_false_start():
    engine = GoldsprintEngine()
    engine.false_start_threshold = 20
    engine.countdown = 3
    
    # P1 pedaling too fast during countdown
    error = engine.update_tick(25, 0, 1)
    assert error == "FALSE START: PLAYER 1"
    
    # P2 pedaling too fast
    error = engine.update_tick(0, 25, 1)
    assert error == "FALSE START: PLAYER 2"
