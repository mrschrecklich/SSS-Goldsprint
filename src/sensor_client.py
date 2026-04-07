import asyncio
import time
import logging
from typing import Callable, Awaitable
from src.engine import GoldsprintEngine

logger = logging.getLogger(__name__)

class SensorClient:
    """
    Background client that connects to a TCP sensor and updates the game engine.
    Implements auto-reconnection and state broadcasting.
    """

    def __init__(self, host: str, port: int, engine: GoldsprintEngine, broadcast_callback: Callable[[], Awaitable[None]]):
        """
        Initializes the sensor client.

        Args:
            host (str): Sensor host IP.
            port (int): Sensor port.
            engine (GoldsprintEngine): The game engine to update.
            broadcast_callback (Callable): Async function to broadcast engine state.
        """
        self.host: str = host
        self.port: int = port
        self.engine: GoldsprintEngine = engine
        self.broadcast_callback: Callable[[], Awaitable[None]] = broadcast_callback

    async def listen_forever(self) -> None:
        """
        Main loop for connecting to the sensor and processing data ticks.
        Automatically retries connection if it fails.
        """
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                logger.info(f"Connected to sensor at {self.host}:{self.port}")
                last_tick_time = time.time()
                
                buffer = ""
                while True:
                    data = await reader.read(1024)
                    if not data:
                        logger.warning("Sensor connection closed by remote host.")
                        break
                    
                    buffer += data.decode()
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Use current engine values as fallback
                        rpm1, rpm2 = self.engine.p1["rpm"], self.engine.p2["rpm"]
                        
                        if line.startswith('P1:'):
                            try:
                                rpm1 = int(line.split(':')[1])
                                self.engine.p1["rpm"] = rpm1
                            except (ValueError, IndexError):
                                pass
                        elif line.startswith('P2:'):
                            try:
                                rpm2 = int(line.split(':')[1])
                                self.engine.p2["rpm"] = rpm2
                            except (ValueError, IndexError):
                                pass
                    
                    now = time.time()
                    dt = now - last_tick_time
                    last_tick_time = now
                    
                    # Update engine with new RPM values (engine.update_tick handles physics)
                    error = self.engine.update_tick(self.engine.p1["rpm"], self.engine.p2["rpm"], dt)
                    if error:
                        self.engine.abort(error)
                    
                    # Notify UI of state change
                    await self.broadcast_callback()
                    
                writer.close()
                await writer.wait_closed()
            except (ConnectionRefusedError, OSError):
                # Silent retry every 2 seconds if sensor is offline
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Sensor Client Error: {e}")
                await asyncio.sleep(2)
