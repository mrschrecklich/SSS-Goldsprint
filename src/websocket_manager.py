import json
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages active WebSocket connections and handles state broadcasting.
    """

    def __init__(self):
        """Initializes the connection manager with an empty set of active connections."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accepts a new WebSocket connection and adds it to the active pool.

        Args:
            websocket (WebSocket): The WebSocket connection to add.
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Removes a WebSocket connection from the active pool.

        Args:
            websocket (WebSocket): The WebSocket connection to remove.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, state: Dict[str, Any]) -> None:
        """
        Broadcasts the current game state to all connected WebSockets.

        Args:
            state (Dict[str, Any]): The serializable state to broadcast.
        """
        if not self.active_connections:
            return
        
        message = json.dumps(state)
        disconnected: Set[WebSocket] = set()
        
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send state to WebSocket: {e}")
                disconnected.add(ws)
                
        for ws in disconnected:
            self.disconnect(ws)

# Global connection manager instance
manager = ConnectionManager()
