import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from src.config import config
from src.engine import GoldsprintEngine
from src.bracket import BracketManager
from src.websocket_manager import manager
from src.sensor_client import SensorClient

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

def get_full_state() -> Dict[str, Any]:
    """Helper to merge engine and bracket states for broadcasting."""
    state = engine.get_state()
    state["bracketState"] = bracket_manager.get_state()
    return state

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
                    error = bracket_manager.add_participant(cmd.get("category"), cmd.get("name"))
                    if error:
                        # Send error back to the requester only or broadcast
                        await websocket.send_text(json.dumps({"type": "ERROR", "message": error}))
                        return # Skip the broadcast_state below to avoid redundant updates
                elif msg_type == "REMOVE_PARTICIPANT":
                    bracket_manager.remove_participant(cmd.get("category"), cmd.get("name"))
                elif msg_type == "RENAME_CATEGORY":
                    bracket_manager.rename_category(cmd.get("old_name"), cmd.get("new_name"))
                elif msg_type == "GENERATE_BRACKET":
                    bracket_manager.generate_bracket(cmd.get("category"))
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
                    bracket_manager.advance_winner(
                        cmd.get("category"), cmd.get("match_id"), 
                        cmd.get("winner"), cmd.get("time")
                    )
                    # Auto-reset race state when a winner advances
                    if bracket_manager.active_match and bracket_manager.active_match.get("id") == cmd.get("match_id"):
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
