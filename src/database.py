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
                    race_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(participant_id) REFERENCES participants(id)
                )
            """)
            
            # Indexes for faster querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_participant ON results(participant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_date ON results(race_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_category ON results(category)")
            
            conn.commit()
            logger.info("Database initialized successfully.")

    def save_race_result(self, name: str, category: str, race_time: float) -> None:
        """
        Saves a race result to the database.
        Automatically adds the participant if they don't exist.

        Args:
            name (str): The rider's name.
            category (str): Race category (e.g., 'OPEN', 'WTNB').
            race_time (float): The rider's finish time in seconds.
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
                "INSERT INTO results (participant_id, category, race_time) VALUES (?, ?, ?)",
                (participant_id, category, race_time)
            )
            
            conn.commit()
            logger.info(f"Saved result: {name} ({category}) - {race_time:.3f}s")

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
            List[Dict[str, Any]]: List of results with time, date, and category.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.race_time, r.race_date, r.category
                FROM results r
                JOIN participants p ON r.participant_id = p.id
                WHERE p.name = ?
                ORDER BY r.race_time ASC
            """, (name,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_highscores(self, category: Optional[str] = None, time_filter: str = "all") -> List[Dict[str, Any]]:
        """
        Retrieves the top times based on category and time filters.

        Args:
            category (Optional[str]): 'OPEN', 'WTNB', or None for all.
            time_filter (str): 'today', 'past 5 days', 'this year', 'all'.

        Returns:
            List[Dict[str, Any]]: List of highscores.
        """
        date_condition = ""
        params = []
        
        # Build time filter
        if time_filter == "today":
            date_condition = "AND r.race_date >= date('now', 'localtime')"
        elif time_filter == "past 5 days":
            date_condition = "AND r.race_date >= date('now', '-5 days', 'localtime')"
        elif time_filter == "this year":
            date_condition = "AND r.race_date >= date('now', 'start of year', 'localtime')"
            
        # Build category filter
        category_condition = ""
        if category:
            category_condition = "AND r.category = ?"
            params.append(category)
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"""
                SELECT p.name, r.race_time, r.race_date, r.category
                FROM results r
                JOIN participants p ON r.participant_id = p.id
                WHERE 1=1 {date_condition} {category_condition}
                ORDER BY r.race_time ASC
                LIMIT 50
            """
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

# Global DB instance
db = GoldsprintDB()
