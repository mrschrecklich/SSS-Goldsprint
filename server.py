import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Set, Callable, Awaitable
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

# --- Configuration ---
PORT = 3000
SENSOR_HOST = '127.0.0.1'
SENSOR_PORT = 5000

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoldsprintEngine:
    """
    Authoritative game engine for the Goldsprint race simulation.
    Handles state management, countdown logic, and physics calculations.
    """
    def __init__(self):
        self.target_dist: float = 500.0
        self.circumference: float = 2.1
        self.false_start_threshold: int = 20
        self.countdown_task: Optional[asyncio.Task] = None
        self.reset()

    def reset(self) -> None:
        """Resets the race state to idle."""
        self.is_racing: bool = False
        self.countdown: Optional[int] = None
        self.winner: Optional[str] = None
        self.race_start_time: Optional[float] = None
        
        # Player data: rpm, speed (km/h), dist (m), finishTime (s)
        self.p1: Dict[str, Any] = {"rpm": 0, "speed": 0, "dist": 0, "finishTime": None}
        self.p2: Dict[str, Any] = {"rpm": 0, "speed": 0, "dist": 0, "finishTime": None}
        
        self._cancel_countdown()

    def _cancel_countdown(self) -> None:
        """Cancels any running countdown task."""
        if self.countdown_task and not self.countdown_task.done():
            self.countdown_task.cancel()
        self.countdown_task = None

    async def start_countdown(self, broadcast_callback: Callable[[], Awaitable[None]]) -> None:
        """Initiates the 3-second countdown sequence."""
        self._cancel_countdown()
        self.reset()
        self.countdown = 3
        await broadcast_callback()
        
        self.countdown_task = asyncio.create_task(self._countdown_loop(broadcast_callback))

    async def _countdown_loop(self, broadcast_callback: Callable[[], Awaitable[None]]) -> None:
        """Internal loop for decrementing the race countdown."""
        try:
            while self.countdown is not None:
                await asyncio.sleep(1)
                if self.countdown is None: break
                
                self.countdown -= 1
                
                if self.countdown == 0:
                    # Race officially starts
                    self.is_racing = True
                    self.race_start_time = time.time()
                elif self.countdown < 0:
                    # Clear the 'GO!' text from UI after a second
                    self.countdown = None
                    await broadcast_callback()
                    break
                
                await broadcast_callback()
        except asyncio.CancelledError:
            logger.info("Countdown task cancelled.")

    def abort(self, reason: Optional[str] = None) -> None:
        """Aborts the race immediately."""
        self._cancel_countdown()
        self.is_racing = False
        self.countdown = None
        if reason:
            self.winner = reason
            logger.info(f"Race aborted. Reason: {reason}")

    def update_tick(self, p1_rpm: int, p2_rpm: int, dt: float) -> Optional[str]:
        """
        Processes a sensor update.
        Returns an error message string if a false start is detected.
        """
        # False start check during countdown
        if self.countdown is not None and self.countdown > 0:
            if p1_rpm > self.false_start_threshold: return 'FALSE START: PLAYER 1'
            if p2_rpm > self.false_start_threshold: return 'FALSE START: PLAYER 2'

        self.p1["rpm"] = p1_rpm
        self.p2["rpm"] = p2_rpm

        # Calculate m/s: (RPM / 60) * circumference
        p1_ms = (p1_rpm / 60) * self.circumference
        p2_ms = (p2_rpm / 60) * self.circumference

        # Convert to km/h for the UI
        self.p1["speed"] = p1_ms * 3.6
        self.p2["speed"] = p2_ms * 3.6

        if self.is_racing:
            self._update_player_progress('p1', p1_ms, dt)
            self._update_player_progress('p2', p2_ms, dt)

            # Auto-stop when both players cross the finish line
            if self.p1["finishTime"] and self.p2["finishTime"]:
                self.is_racing = False
        return None

    def _update_player_progress(self, player_key: str, speed_ms: float, dt: float) -> None:
        """Updates distance and checks for finish line cross."""
        player = getattr(self, player_key)
        if player["finishTime"]: return

        player["dist"] += speed_ms * dt
        if player["dist"] >= self.target_dist:
            player["dist"] = self.target_dist
            player["finishTime"] = time.time() - self.race_start_time
            if not self.winner:
                self.winner = 'Player 1' if player_key == 'p1' else 'Player 2'
                logger.info(f"Winner detected: {self.winner}")

    def get_state(self) -> Dict[str, Any]:
        """Returns the serializable state of the engine."""
        return {
            "isRacing": self.is_racing,
            "countdown": self.countdown,
            "targetDist": self.target_dist,
            "circumference": self.circumference,
            "falseStartThreshold": self.false_start_threshold,
            "winner": self.winner,
            "p1": self.p1,
            "p2": self.p2
        }

# --- Global State ---
engine = GoldsprintEngine()
active_connections: Set[WebSocket] = set()

async def broadcast() -> None:
    """Broadcasts the current game state to all connected WebSockets."""
    if not active_connections: return
    
    message = json.dumps(engine.get_state())
    disconnected = set()
    
    # We use list() to avoid "Set changed size during iteration"
    for ws in list(active_connections):
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
            
    for ws in disconnected:
        if ws in active_connections:
            active_connections.remove(ws)

async def sensor_listener_task() -> None:
    """
    Background task that connects to the TCP sensor and updates the engine.
    Implements auto-reconnection.
    """
    while True:
        try:
            reader, writer = await asyncio.open_connection(SENSOR_HOST, SENSOR_PORT)
            logger.info(f"Connected to sensor at {SENSOR_HOST}:{SENSOR_PORT}")
            last_tick_time = time.time()
            
            while True:
                data = await reader.read(1024)
                if not data: break # Socket closed
                
                lines = data.decode().split('\n')
                rpm1, rpm2 = engine.p1["rpm"], engine.p2["rpm"]
                
                for line in lines:
                    if line.startswith('P1:'):
                        try: rpm1 = int(line.split(':')[1])
                        except (ValueError, IndexError): pass
                    elif line.startswith('P2:'):
                        try: rpm2 = int(line.split(':')[1])
                        except (ValueError, IndexError): pass
                
                now = time.time()
                dt = now - last_tick_time
                last_tick_time = now
                
                error = engine.update_tick(rpm1, rpm2, dt)
                if error:
                    engine.abort(error)
                
                await broadcast()
                
            writer.close()
            await writer.wait_closed()
        except (ConnectionRefusedError, OSError):
            # Silent retry every 2 seconds if sensor is offline
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Sensor Client Error: {e}")
            await asyncio.sleep(2)

# --- FastAPI Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start sensor background task
    task = asyncio.create_task(sensor_listener_task())
    yield
    # Shutdown: Cleanup
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass

app = FastAPI(lifespan=lifespan)

@app.websocket("/")
async def websocket_handler(websocket: WebSocket):
    """Handles incoming WebSocket connections from Admin and Audience views."""
    await websocket.accept()
    active_connections.add(websocket)
    
    # Send initial state
    await websocket.send_text(json.dumps(engine.get_state()))
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                msg_type = cmd.get("type")
                
                if msg_type == "START":
                    await engine.start_countdown(broadcast)
                elif msg_type == "STOP":
                    engine.abort()
                elif msg_type == "RESET":
                    engine.reset()
                elif msg_type == "CONFIG":
                    if "dist" in cmd: engine.target_dist = float(cmd["dist"])
                    if "circ" in cmd: engine.circumference = float(cmd["circ"])
                    if "fsThreshold" in cmd: engine.false_start_threshold = int(cmd["fsThreshold"])
                
                await broadcast()
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Invalid WS message: {e}")
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

# Serve static UI files
app.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Goldsprint Server on port {PORT}...")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, log_level="warning")
