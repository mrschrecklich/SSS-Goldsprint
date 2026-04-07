import sqlite3
import logging
import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class GoldsprintDB:
    """
    Manages the SQLite database for SSS-Goldsprint.
    Handles persistence for participants and race results.
    """

    def __init__(self, db_path: str = "goldsprint.db"):
        """
        Initializes the database connection.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Participants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL COLLATE NOCASE
                )
            """)
            
            # Race results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    race_time REAL NOT NULL,
                    race_distance REAL NOT NULL DEFAULT 500.0,
                    race_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(participant_id) REFERENCES participants(id)
                )
            """)
            
            # Ensure race_distance exists if the table was already there (migration)
            try:
                cursor.execute("ALTER TABLE results ADD COLUMN race_distance REAL NOT NULL DEFAULT 500.0")
            except sqlite3.OperationalError:
                pass # Already exists
            
            # Indexes for faster querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_participant ON results(participant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_date ON results(race_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_category ON results(category)")
            
            conn.commit()
            logger.info("Database initialized successfully.")

    def save_race_result(self, name: str, category: str, race_time: float, distance: float) -> None:
        """
        Saves a race result to the database.
        Automatically adds the participant if they don't exist.

        Args:
            name (str): The rider's name.
            category (str): Race category (e.g., 'OPEN', 'WTNB').
            race_time (float): The rider's finish time in seconds.
            distance (float): The race distance in meters.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert or ignore participant
            cursor.execute("INSERT OR IGNORE INTO participants (name) VALUES (?)", (name,))
            
            # Get participant id
            cursor.execute("SELECT id FROM participants WHERE name = ?", (name,))
            participant_id = cursor.fetchone()["id"]
            
            # Insert result
            cursor.execute(
                "INSERT INTO results (participant_id, category, race_time, race_distance) VALUES (?, ?, ?, ?)",
                (participant_id, category, race_time, distance)
            )
            
            conn.commit()
            logger.info(f"Saved result: {name} ({category}) - {race_time:.3f}s for {distance}m")

    def delete_participant(self, name: str) -> None:
        """
        Deletes a participant and all their associated race results.

        Args:
            name (str): The rider's name.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM participants WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                participant_id = row["id"]
                cursor.execute("DELETE FROM results WHERE participant_id = ?", (participant_id,))
                cursor.execute("DELETE FROM participants WHERE id = ?", (participant_id,))
                conn.commit()
                logger.info(f"Deleted participant and all data for: {name}")

    def clear_all_data(self) -> None:
        """Wipes all participants and results from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM results")
            cursor.execute("DELETE FROM participants")
            conn.commit()
            logger.info("All database data cleared.")

    def get_name_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Returns names matching a partial query for autocomplete.

        Args:
            query (str): The partial name to search for.
            limit (int): Maximum number of results.

        Returns:
            List[str]: List of matching names.
        """
        if not query:
            return []
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM participants WHERE name LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            )
            return [row["name"] for row in cursor.fetchall()]

    def get_participant_stats(self, name: str) -> List[Dict[str, Any]]:
        """
        Retrieves all race times for a specific rider.

        Args:
            name (str): The rider's name.

        Returns:
            List[Dict[str, Any]]: List of results with time, date, category, and speed.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.race_time, r.race_distance, r.race_date, r.category,
                (r.race_distance / r.race_time * 3.6) as avg_speed_kmh
                FROM results r
                JOIN participants p ON r.participant_id = p.id
                WHERE p.name = ?
                ORDER BY r.race_time ASC
            """, (name,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_rider_best_times(self, name: str, distance: Optional[float] = None) -> Dict[str, Optional[float]]:
        """
        Returns tournament best (for current distance) and all-time best times for a rider.

        Args:
            name (str): The rider's name.
            distance (Optional[float]): The current tournament race distance.

        Returns:
            Dict[str, Optional[float]]: {'tournament': float|None, 'all_time': float|None}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # All-time best (any distance)
            cursor.execute("""
                SELECT MIN(r.race_time) as best
                FROM results r
                JOIN participants p ON r.participant_id = p.id
                WHERE p.name = ?
            """, (name,))
            all_time = cursor.fetchone()["best"]
            
            # Tournament best (specific to current distance)
            tournament_best = None
            if distance is not None:
                cursor.execute("""
                    SELECT MIN(r.race_time) as best
                    FROM results r
                    JOIN participants p ON r.participant_id = p.id
                    WHERE p.name = ? AND r.race_distance = ?
                """, (name, distance))
                tournament_best = cursor.fetchone()["best"]
            
            return {"tournament": tournament_best, "all_time": all_time}

    def get_highscores(self, category: Optional[str] = None, time_filter: str = "all", distance: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the top times based on category, time, and distance filters.

        Args:
            category (Optional[str]): 'OPEN', 'WTNB', or None for all.
            time_filter (str): 'today', 'past 5 days', 'this year', 'all'.
            distance (Optional[float]): Filter by specific distance.

        Returns:
            List[Dict[str, Any]]: List of highscores.
        """
        conditions = ["1=1"]
        params = []
        
        # Build time filter
        if time_filter == "today":
            conditions.append("r.race_date >= date('now', 'localtime')")
        elif time_filter == "past 5 days":
            conditions.append("r.race_date >= date('now', '-5 days', 'localtime')")
        elif time_filter == "this year":
            conditions.append("r.race_date >= date('now', 'start of year', 'localtime')")
            
        # Build category filter
        if category:
            conditions.append("r.category = ?")
            params.append(category)

        # Build distance filter
        if distance:
            conditions.append("r.race_distance = ?")
            params.append(distance)
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # If a specific distance is selected, we sort by time.
            # If no distance is selected, we sort by average speed.
            order_by = "r.race_time ASC" if distance else "(r.race_distance / r.race_time) DESC"
            
            query = f"""
                SELECT p.name, r.race_time, r.race_distance, r.race_date, r.category,
                (r.race_distance / r.race_time * 3.6) as avg_speed_kmh
                FROM results r
                JOIN participants p ON r.participant_id = p.id
                WHERE {" AND ".join(conditions)}
                ORDER BY {order_by}
                LIMIT 50
            """
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

# Global DB instance
db = GoldsprintDB()
