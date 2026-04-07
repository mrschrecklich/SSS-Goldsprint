import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

class GoldsprintEngine:
    """
    Authoritative game engine for the Goldsprint race simulation.
    Handles state management, countdown logic, and physics calculations.
    """

    def __init__(self, target_dist: float = 500.0, circumference: float = 2.1, false_start_threshold: int = 20):
        """
        Initializes the Goldsprint race engine.

        Args:
            target_dist (float): Target race distance in meters.
            circumference (float): Wheel circumference in meters.
            false_start_threshold (int): RPM threshold for false start detection.
        """
        self.target_dist: float = max(0.1, target_dist)
        self.circumference: float = max(0.1, circumference)
        self.false_start_threshold: int = max(1, false_start_threshold)
        
        self.is_racing: bool = False
        self.countdown: Optional[int] = None
        self.winner: Optional[str] = None
        self.race_start_time: Optional[float] = None
        self.countdown_task: Optional[asyncio.Task] = None
        
        # Player data: rpm, speed (km/h), dist (m), finishTime (s)
        self.p1: Dict[str, Any] = {"rpm": 0, "speed": 0, "dist": 0, "finishTime": None}
        self.p2: Dict[str, Any] = {"rpm": 0, "speed": 0, "dist": 0, "finishTime": None}

    def reset(self) -> None:
        """Resets the race state to idle and cancels any active countdown."""
        self.is_racing = False
        self.countdown = None
        self.winner = None
        self.race_start_time = None
        
        self.p1 = {"rpm": 0, "speed": 0, "dist": 0, "finishTime": None}
        self.p2 = {"rpm": 0, "speed": 0, "dist": 0, "finishTime": None}
        
        self._cancel_countdown()

    def _cancel_countdown(self) -> None:
        """Cancels any running countdown task."""
        if self.countdown_task and not self.countdown_task.done():
            self.countdown_task.cancel()
        self.countdown_task = None

    async def start_countdown(self, broadcast_callback: Callable[[], Awaitable[None]]) -> None:
        """
        Initiates the 3-second countdown sequence.

        Args:
            broadcast_callback (Callable): Async function called after each tick to broadcast state.
        """
        self._cancel_countdown()
        self.reset()
        self.countdown = 3
        await broadcast_callback()
        
        self.countdown_task = asyncio.create_task(self._countdown_loop(broadcast_callback))

    async def _countdown_loop(self, broadcast_callback: Callable[[], Awaitable[None]]) -> None:
        """
        Internal loop for decrementing the race countdown.

        Args:
            broadcast_callback (Callable): Async function called after each tick.
        """
        try:
            while self.countdown is not None:
                await asyncio.sleep(1)
                if self.countdown is None:
                    break
                
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
        """
        Aborts the race immediately.

        Args:
            reason (Optional[str]): The reason for aborting (e.g., 'FALSE START').
        """
        self._cancel_countdown()
        self.is_racing = False
        self.countdown = None
        if reason:
            self.winner = reason
            logger.info(f"Race aborted. Reason: {reason}")

    def update_tick(self, p1_rpm: int, p2_rpm: int, dt: float) -> Optional[str]:
        """
        Processes a sensor update tick.

        Args:
            p1_rpm (int): Current RPM for Player 1.
            p2_rpm (int): Current RPM for Player 2.
            dt (float): Time elapsed since the last tick in seconds.

        Returns:
            Optional[str]: An error message if a false start is detected, otherwise None.
        """
        # False start check during countdown
        if self.countdown is not None and self.countdown > 0:
            if p1_rpm > self.false_start_threshold:
                return 'FALSE START: PLAYER 1'
            if p2_rpm > self.false_start_threshold:
                return 'FALSE START: PLAYER 2'

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
        """
        Updates distance and checks for finish line cross for a specific player.

        Args:
            player_key (str): 'p1' or 'p2'.
            speed_ms (float): Speed in meters per second.
            dt (float): Delta time in seconds.
        """
        player = self.p1 if player_key == 'p1' else self.p2
        if player["finishTime"]:
            return

        player["dist"] += speed_ms * dt
        if player["dist"] >= self.target_dist:
            player["dist"] = self.target_dist
            if self.race_start_time is not None:
                player["finishTime"] = time.time() - self.race_start_time
            if not self.winner:
                self.winner = 'Player 1' if player_key == 'p1' else 'Player 2'
                logger.info(f"Winner detected: {self.winner}")

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the serializable state of the engine.

        Returns:
            Dict[str, Any]: The engine's current state.
        """
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
