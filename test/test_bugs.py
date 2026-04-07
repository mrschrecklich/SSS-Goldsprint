import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.engine import GoldsprintEngine
from src.sensor_client import SensorClient
from src.database import GoldsprintDB
from src.bracket import BracketManager

@pytest.mark.asyncio
async def test_tcp_fragmentation_bug():
    """
    REPRODUCTION: Bug #2 (TCP Splitting).
    We simulate the sensor sending "P1:1" and then "00\n" in two separate TCP packets.
    The current implementation should FAIL to record 100 RPM.
    """
    engine = GoldsprintEngine()
    # Mock the broadcast callback
    callback = AsyncMock()
    client = SensorClient("127.0.0.1", 5000, engine, callback)
    
    # Mock the TCP reader to return data in fragments
    mock_reader = AsyncMock()
    mock_reader.read.side_effect = [
        b"P1:1",    # Fragment 1
        b"00\n",    # Fragment 2
        b""         # Connection close
    ]
    mock_writer = MagicMock()
    
    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
        # We run the listener briefly. It will process the fragments.
        # We use wait_for to prevent it from looping forever.
        try:
            await asyncio.wait_for(client.listen_forever(), timeout=0.1)
        except (asyncio.TimeoutError, StopIteration):
            pass
            
    # If the bug exists, the RPM will likely be 0 or 1, not 100.
    assert engine.p1["rpm"] == 100, f"Expected 100 RPM, got {engine.p1['rpm']}"

@pytest.mark.asyncio
async def test_race_start_concurrency_bug():
    """
    REPRODUCTION: Bug #4 (Race Start Race Condition).
    Triggering start_countdown twice should not result in multiple tasks or double-decrements.
    """
    engine = GoldsprintEngine()
    callback = AsyncMock()
    
    # Start first countdown
    await engine.start_countdown(callback)
    task1 = engine.countdown_task
    
    # Start second countdown immediately
    await engine.start_countdown(callback)
    task2 = engine.countdown_task
    
    # We want to ensure it's still the SAME task (the second one was ignored)
    assert task1 == task2, "A new task was created when it should have been ignored!"
    assert not task1.cancelled(), "Original task was incorrectly cancelled!"

def test_database_zero_division_bug(tmp_path):
    """
    REPRODUCTION: Bug #5 (Zero-Division Hazard).
    Calculating highscores when a race time is 0 should NOT crash the query.
    """
    db_file = tmp_path / "test.db"
    db = GoldsprintDB(str(db_file))
    
    # Save a "corrupt" result with 0.0 seconds
    db.save_race_result("GlitchRider", "OPEN", 0.0, 500.0)
    
    # This call should not raise ZeroDivisionError (sqlite3 error)
    try:
        results = db.get_highscores(distance=500.0)
        assert len(results) > 0
    except Exception as e:
        pytest.fail(f"Highscore query crashed on zero time: {e}")

@pytest.mark.asyncio
async def test_stale_engine_state_bug():
    """
    REPRODUCTION: Bug #6 (Stale Engine State).
    If a race is finished, then RESET, the finish times must be NULL.
    """
    engine = GoldsprintEngine(target_dist=10)
    # Simulate a finished race for P1
    engine.is_racing = True
    engine.race_start_time = 1000.0
    engine.update_tick(100, 0, 1.0) # Move P1 forward
    
    # Ensure P1 finished
    engine.p1["dist"] = 10
    engine.p1["finishTime"] = 5.0
    
    # Now RESET
    engine.reset()
    
    assert engine.p1["finishTime"] is None, "P1 finishTime remained after reset!"
    assert engine.winner is None, "Winner remained after reset!"

@pytest.mark.asyncio
async def test_bracket_auto_advance_stale_data():
    """
    REPRODUCTION: Bug #6 (Deeper logic).
    Ensures that ADVANCE_WINNER doesn't use old engine data.
    """
    # This is a logic test for src/main.py logic, but we can test BracketManager logic here.
    # We'll simulate the state where engine has data, but match is advanced.
    engine = GoldsprintEngine()
    engine.p1["finishTime"] = 10.5
    
    bracket = BracketManager()
    bracket.add_participant("OPEN", "Rider A")
    bracket.add_participant("OPEN", "Rider B")
    bracket.generate_bracket("OPEN")
    
    match_id = bracket.categories["OPEN"]["bracket"][0][0]["id"]
    
    # Advance winner manually
    bracket.advance_winner("OPEN", match_id, "Rider A", winner_time=None)
    
    # The fix for this bug is actually in how main.py handles the message, 
    # ensuring it doesn't just pull whatever is in engine.p1["finishTime"].
    pass 

def test_mid_race_state_corruption():
    """
    REPRODUCTION: Bug #3 & #4 (State Corruption / Mid-Race Mutation).
    Sending a bracket-mutating command while engine.is_racing == True should be ignored.
    """
    from fastapi.testclient import TestClient
    from src.main import app, engine, bracket_manager
    import json
    
    # Force engine into racing state
    engine.is_racing = True
    
    # Store old active category
    old_active_category = bracket_manager.active_category
    
    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        # Attempt to change active category mid-race
        websocket.send_text(json.dumps({"type": "SET_ACTIVE_CATEGORY", "category": "WTNB"}))
        
        # We need to receive the broadcasted state or check backend directly
        # Easiest way is to just check the bracket_manager directly since it's the same instance
        # if the test fails, bracket_manager.active_category will be "WTNB".
        
    assert bracket_manager.active_category == old_active_category, "Category changed mid-race! State corrupted."
    
    # Cleanup
    engine.is_racing = False

def test_advance_winner_engine_reset_bug():
    """
    REPRODUCTION: Bug 1 (Tournament Race Concurrency).
    Advancing the winner must correctly reset the engine state, regardless of whether 
    bracket_manager.active_match was updated. If it fails, stale finish times leak into the next heat.
    """
    from fastapi.testclient import TestClient
    from src.main import app, engine, bracket_manager
    import json
    
    # 1. Setup a bracket with 4 players
    bracket_manager.categories["OPEN"]["participants"] = ["A", "B", "C", "D"]
    bracket_manager.generate_bracket("OPEN")
    
    # 2. Start a race and set finish times
    engine.reset()
    engine.p1["finishTime"] = 10.0
    engine.p2["finishTime"] = 12.0
    engine.winner = 'Player 1'
    engine.is_racing = False  # Engine auto-stops when both finish
    
    # 3. Get the first active match ID
    active_match = bracket_manager.active_match
    assert active_match is not None
    mid = active_match["id"]
    
    # 4. Simulate the Admin clicking 'ACK WINNER' via Websocket
    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        # Ignore initial state broadcast
        websocket.receive_text()
        
        websocket.send_text(json.dumps({
            "type": "ADVANCE_WINNER",
            "category": "OPEN",
            "match_id": mid,
            "winner": "A",
            "time": 10.0
        }))
        
        # Wait for the server to process the command and send the updated state
        new_state = websocket.receive_text()
        assert "A" in new_state
        
    # BUG ASSERTION: The engine MUST have been reset. 
    # If the bug exists, engine.p1["finishTime"] will STILL be 10.0
    assert engine.p1["finishTime"] is None, "BUG 1 CONFIRMED: Engine failed to reset after ADVANCE_WINNER, leaking stale finish times to the next heat!"
    assert engine.winner is None, "BUG 1 CONFIRMED: Engine winner state failed to reset!"
