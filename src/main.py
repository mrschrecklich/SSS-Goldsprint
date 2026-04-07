import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from src.config import config
from src.engine import GoldsprintEngine
from src.bracket import BracketManager
from src.websocket_manager import manager
from src.sensor_client import SensorClient
from src.database import db

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Core system components
engine = GoldsprintEngine(
    target_dist=config.default_target_dist,
    circumference=config.default_circumference,
    false_start_threshold=config.false_start_threshold
)
bracket_manager = BracketManager()

# Cache for best times to avoid DB hits on every sensor tick
_best_times_cache = {}

def get_full_state() -> Dict[str, Any]:
    """Helper to merge engine and bracket states for broadcasting."""
    state = engine.get_state()
    bracket_state = bracket_manager.get_state()
    
    # Use cached best times, only fetch from DB if missing
    participants_bests = {}
    for cat_name, cat_data in bracket_state["categories"].items():
        for name in cat_data["participants"]:
            if name not in participants_bests:
                if name not in _best_times_cache:
                    _best_times_cache[name] = db.get_rider_best_times(name)
                participants_bests[name] = _best_times_cache[name]
    
    bracket_state["participants_bests"] = participants_bests
    state["bracketState"] = bracket_state
    return state

def invalidate_bests_cache(name: Optional[str] = None):
    """Clears the best times cache for one or all riders."""
    global _best_times_cache
    if name:
        _best_times_cache.pop(name, None)
    else:
        _best_times_cache = {}

async def broadcast_state() -> None:
    """Async helper to broadcast the merged state to all UIs."""
    await manager.broadcast(get_full_state())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles background tasks during the application lifecycle."""
    # Startup: Initialize sensor client background task
    sensor_client = SensorClient(
        host=config.sensor_host,
        port=config.sensor_port,
        engine=engine,
        broadcast_callback=broadcast_state
    )
    sensor_task = asyncio.create_task(sensor_client.listen_forever())
    logger.info("Application lifespan started: sensor client initialized.")
    
    yield
    
    # Shutdown: Clean up background tasks
    sensor_task.cancel()
    try:
        await sensor_task
    except asyncio.CancelledError:
        pass
    logger.info("Application lifespan ended: sensor client stopped.")

app = FastAPI(lifespan=lifespan, title="Goldsprint SSS Server")

# --- REST API Endpoints ---

@app.get("/api/suggestions")
async def get_suggestions(q: str = ""):
    """Returns participant name suggestions for autocomplete."""
    return db.get_name_suggestions(q)

@app.get("/api/participant/{name}")
async def get_participant_stats(name: str):
    """Returns all race times for a specific participant."""
    stats = db.get_participant_stats(name)
    if not stats:
        return JSONResponse(status_code=404, content={"message": "Participant not found"})
    return stats

@app.get("/api/highscores")
async def get_highscores(category: str = None, filter: str = "all", distance: float = None):
    """Returns leaderboard data based on category, time, and distance filters."""
    # Map 'All' from UI to None for DB
    db_cat = None if category == "All" else category
    return db.get_highscores(category=db_cat, time_filter=filter, distance=distance)

@app.delete("/api/participant/{name}")
async def delete_participant(name: str):
    """Deletes a participant and all their data."""
    db.delete_participant(name)
    invalidate_bests_cache(name)
    return {"message": f"Deleted {name}"}

@app.delete("/api/participants/all")
async def delete_all_participants():
    """Wipes the entire database history."""
    db.clear_all_data()
    invalidate_bests_cache()
    return {"message": "All data cleared"}

@app.get("/api/rider_bests/{name}")
async def get_rider_bests(name: str):
    """Returns today's and all-time best times for a rider."""
    return db.get_rider_best_times(name)

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for Admin and Audience views.
    Handles command processing and real-time updates.
    """
    await manager.connect(websocket)
    
    # Send current state upon connection
    await websocket.send_text(json.dumps(get_full_state()))
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                msg_type = cmd.get("type")
                
                # --- Race Control ---
                if msg_type == "START":
                    bracket_manager.show_bracket = False
                    await engine.start_countdown(broadcast_state)
                elif msg_type == "STOP":
                    engine.abort()
                elif msg_type == "RESET":
                    engine.reset()
                elif msg_type == "CONFIG":
                    if "dist" in cmd: engine.target_dist = max(0.1, float(cmd["dist"]))
                    if "circ" in cmd: engine.circumference = max(0.1, float(cmd["circ"]))
                    if "fsThreshold" in cmd: engine.false_start_threshold = max(1, int(cmd["fsThreshold"]))
                
                # --- Bracket Control ---
                elif msg_type == "ADD_PARTICIPANT":
                    name = cmd.get("name")
                    error = bracket_manager.add_participant(cmd.get("category"), name)
                    if error:
                        # Send error back to the requester only or broadcast
                        await websocket.send_text(json.dumps({"type": "ERROR", "message": error}))
                        return # Skip the broadcast_state below to avoid redundant updates
                    invalidate_bests_cache(name)
                elif msg_type == "REMOVE_PARTICIPANT":
                    bracket_manager.remove_participant(cmd.get("category"), cmd.get("name"))
                elif msg_type == "RENAME_CATEGORY":
                    bracket_manager.rename_category(cmd.get("old_name"), cmd.get("new_name"))
                elif msg_type == "GENERATE_BRACKET":
                    bracket_manager.generate_bracket(cmd.get("category"))
                elif msg_type == "MANUAL_ADVANCE":
                    bracket_manager.manual_advance(
                        cmd.get("category"),
                        cmd.get("match_id"),
                        cmd.get("winner")
                    )
                elif msg_type == "SWAP_PARTICIPANTS":
                    bracket_manager.swap_participants(
                        cmd.get("category"), cmd.get("match1_id"), cmd.get("p1_idx"),
                        cmd.get("match2_id"), cmd.get("p2_idx")
                    )
                elif msg_type == "SET_ACTIVE_CATEGORY":
                    cat = cmd.get("category")
                    if cat in bracket_manager.categories:
                        bracket_manager.active_category = cat
                elif msg_type == "TOGGLE_BRACKET_VIEW":
                    if not engine.is_racing:
                        bracket_manager.show_bracket = cmd.get("show", False)
                elif msg_type == "SET_ACTIVE_MATCH":
                    match_data = cmd.get("match")
                    bracket_manager.active_match = match_data
                    if match_data and "category" in match_data:
                        bracket_manager.active_category = match_data["category"]
                elif msg_type == "ADVANCE_WINNER":
                    cat = cmd.get("category")
                    mid = cmd.get("match_id")
                    
                    # We need the current race distance from the engine
                    distance = engine.target_dist
                    
                    # Persist results for BOTH players if they finished
                    match = bracket_manager.active_match
                    if match:
                        if engine.p1["finishTime"]:
                            db.save_race_result(match["p1"], cat, engine.p1["finishTime"], distance)
                            invalidate_bests_cache(match["p1"])
                        if engine.p2["finishTime"]:
                            db.save_race_result(match["p2"], cat, engine.p2["finishTime"], distance)
                            invalidate_bests_cache(match["p2"])
                    
                    bracket_manager.advance_winner(
                        cat, mid, 
                        cmd.get("winner"), cmd.get("time")
                    )
                    
                    # Auto-reset race state when a winner advances
                    if bracket_manager.active_match and bracket_manager.active_match.get("id") == mid:
                        bracket_manager.active_match = None
                        if not bracket_manager.champion:
                            bracket_manager.show_bracket = True
                        engine.reset()
                elif msg_type == "ACK_CHAMPION":
                    bracket_manager.clear_champion()
                
                # State changed, broadcast to everyone
                await broadcast_state()
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Malformed command received: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Serve static frontend files from public/ directory
app.mount("/", StaticFiles(directory="public", html=True), name="public")
