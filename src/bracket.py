import random
import uuid
from typing import Dict, Any, Optional, List

class BracketManager:
    """
    Manages tournament brackets, participants, and categories for Goldsprint races.
    Handles bracket generation, winner propagation, and state tracking.
    """

    def __init__(self):
        """Initializes the BracketManager with default categories."""
        self.show_bracket: bool = False
        self.active_category: str = "OPEN"
        self.categories: Dict[str, Dict[str, Any]] = {
            "OPEN": {"name": "OPEN", "participants": [], "bracket": [], "top_times": []},
            "WTNB": {"name": "WTNB", "participants": [], "bracket": [], "top_times": []}
        }
        self.active_match: Optional[Dict[str, Any]] = None
        self.champion: Optional[Dict[str, str]] = None

    def add_participant(self, category: str, name: str) -> Optional[str]:
        """
        Adds a participant to a specific category.
        Enforces uniqueness across all categories.

        Args:
            category (str): The category name.
            name (str): The participant's name.

        Returns:
            Optional[str]: Error message if name is duplicate, otherwise None.
        """
        name = name.strip()
        if not name:
            return "Name cannot be empty."
        if category not in self.categories:
            return f"Category {category} does not exist."
            
        # Check for duplicate in ANY category
        for cat_name, cat_data in self.categories.items():
            if name in cat_data["participants"]:
                return f"'{name}' is already registered in {cat_name} category."
        
        self.categories[category]["participants"].append(name)
        return None
            
    def remove_participant(self, category: str, name: str) -> None:
        """
        Removes a participant from a specific category.

        Args:
            category (str): The category name.
            name (str): The participant's name.
        """
        if category in self.categories and name in self.categories[category]["participants"]:
            self.categories[category]["participants"].remove(name)

    def rename_category(self, old_name: str, new_name: str) -> None:
        """
        Renames an existing category.

        Args:
            old_name (str): The current category name.
            new_name (str): The new category name.
        """
        new_name = new_name.strip()
        if old_name in self.categories and new_name and new_name not in self.categories:
            self.categories[new_name] = self.categories.pop(old_name)
            self.categories[new_name]["name"] = new_name
            if self.active_category == old_name:
                self.active_category = new_name

    def generate_bracket(self, category: str) -> None:
        """
        Generates a single-elimination tournament bracket for a category.

        Args:
            category (str): The category name.
        """
        if category not in self.categories:
            return
        
        participants = list(self.categories[category]["participants"])
        random.shuffle(participants)
        
        num_participants = len(participants)
        if num_participants == 0:
            self.categories[category]["bracket"] = []
            return
            
        # Calculate next power of 2 for a balanced bracket
        power = 1
        while power < num_participants:
            power *= 2
            
        num_byes = power - num_participants
        participants.extend(["BYE"] * num_byes)
        
        # Determine number of rounds
        num_rounds = 0
        p = power
        while p > 1:
            num_rounds += 1
            p //= 2
            
        bracket = [[] for _ in range(num_rounds)]
        
        # Generate Round 1 matches
        r1_matches = []
        for i in range(0, power, 2):
            match_id = str(uuid.uuid4())
            p1 = participants[i]
            p2 = participants[i+1]
            winner = None
            
            if p1 == "BYE" and p2 != "BYE":
                winner = p2
            elif p2 == "BYE" and p1 != "BYE":
                winner = p1
            elif p1 == "BYE" and p2 == "BYE":
                winner = "BYE"
            
            r1_matches.append({
                "id": match_id,
                "p1": p1,
                "p2": p2,
                "winner": winner,
                "next_match_id": None
            })
            
        bracket[0] = r1_matches
        
        # Generate subsequent rounds and link them
        if num_rounds > 1:
            prev_round = bracket[0]
            for r in range(1, num_rounds):
                current_round = []
                for i in range(0, len(prev_round), 2):
                    match_id = str(uuid.uuid4())
                    m1 = prev_round[i]
                    m2 = prev_round[i+1]
                    m1["next_match_id"] = match_id
                    m2["next_match_id"] = match_id
                    
                    p1 = m1["winner"] if m1["winner"] else None
                    p2 = m2["winner"] if m2["winner"] else None
                    winner = None
                    
                    if p1 == "BYE" and p2 != "BYE" and p2 is not None:
                        winner = p2
                    elif p2 == "BYE" and p1 != "BYE" and p1 is not None:
                        winner = p1
                    elif p1 == "BYE" and p2 == "BYE":
                        winner = "BYE"
                    
                    current_round.append({
                        "id": match_id,
                        "p1": p1,
                        "p2": p2,
                        "winner": winner,
                        "next_match_id": None
                    })
                bracket[r] = current_round
                prev_round = current_round
            
        self.categories[category]["bracket"] = bracket
        self._propagate_winners(category)

    def swap_participants(self, category: str, match1_id: str, p1_idx: int, match2_id: str, p2_idx: int) -> None:
        """
        Swaps participants between two matches in the first round.

        Args:
            category (str): The category name.
            match1_id (str): ID of the first match.
            p1_idx (int): Participant index (1 or 2) in the first match.
            match2_id (str): ID of the second match.
            p2_idx (int): Participant index (1 or 2) in the second match.
        """
        if category not in self.categories:
            return
        bracket = self.categories[category]["bracket"]
        if not bracket:
            return
        
        # Only allow swapping in Round 1
        r1 = bracket[0]
        m1 = next((m for m in r1 if m["id"] == match1_id), None)
        m2 = next((m for m in r1 if m["id"] == match2_id), None)
        
        if m1 and m2:
            key1 = "p1" if p1_idx == 1 else "p2"
            key2 = "p1" if p2_idx == 1 else "p2"
            
            m1[key1], m2[key2] = m2[key2], m1[key1]
            
            # Re-evaluate winners for affected matches
            for m in [m1, m2]:
                m["winner"] = None
                if m["p1"] == "BYE" and m["p2"] != "BYE":
                    m["winner"] = m["p2"]
                elif m["p2"] == "BYE" and m["p1"] != "BYE":
                    m["winner"] = m["p1"]
                elif m["p1"] == "BYE" and m["p2"] == "BYE":
                    m["winner"] = "BYE"
            
            self._propagate_winners(category)

    def _propagate_winners(self, category: str) -> None:
        """
        Internal method to propagate winners up through the bracket rounds.

        Args:
            category (str): The category name.
        """
        bracket = self.categories[category]["bracket"]
        if not bracket:
            return
        for r_idx in range(len(bracket) - 1):
            for m in bracket[r_idx]:
                if m["next_match_id"]:
                    next_m = next((nm for nm in bracket[r_idx+1] if nm["id"] == m["next_match_id"]), None)
                    if next_m:
                        idx = bracket[r_idx].index(m)
                        if idx % 2 == 0:
                            next_m["p1"] = m["winner"]
                        else:
                            next_m["p2"] = m["winner"]
                            
                        # Re-evaluate byes for next_m, but don't overwrite real winners
                        if not next_m.get("_actual_winner"):
                            next_m["winner"] = None
                            if next_m["p1"] == "BYE" and next_m["p2"] != "BYE" and next_m["p2"] is not None:
                                next_m["winner"] = next_m["p2"]
                            elif next_m["p2"] == "BYE" and next_m["p1"] != "BYE" and next_m["p1"] is not None:
                                next_m["winner"] = next_m["p1"]
                            elif next_m["p1"] == "BYE" and next_m["p2"] == "BYE":
                                next_m["winner"] = "BYE"

    def advance_winner(self, category: str, match_id: str, winner_name: str, winner_time: Optional[float] = None) -> None:
        """
        Advances a winner to the next round of the bracket.

        Args:
            category (str): The category name.
            match_id (str): ID of the match completed.
            winner_name (str): Name of the winner.
            winner_time (Optional[float]): The winner's race time.
        """
        if category not in self.categories:
            return
        
        # Track top 3 times
        if winner_time:
            self.categories[category]["top_times"].append({"name": winner_name, "time": winner_time})
            self.categories[category]["top_times"].sort(key=lambda x: x["time"])
            self.categories[category]["top_times"] = self.categories[category]["top_times"][:3]

        bracket = self.categories[category]["bracket"]
        for r_idx, round_matches in enumerate(bracket):
            for m in round_matches:
                if m["id"] == match_id:
                    m["winner"] = winner_name
                    m["_actual_winner"] = True
                    self._propagate_winners(category)
                    
                    # Final match detection
                    if r_idx == len(bracket) - 1:
                        self.champion = {"name": winner_name, "category": category}
                    return

    def manual_advance(self, category: str, match_id: str, winner_name: str) -> None:
        """
        Manually advances a participant without a race.

        Args:
            category (str): The category name.
            match_id (str): ID of the match.
            winner_name (str): Name of the participant to advance.
        """
        self.advance_winner(category, match_id, winner_name, winner_time=None)

    def clear_champion(self) -> None:
        """Clears the current champion and returns to bracket view."""
        self.champion = None
        self.show_bracket = True

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the serializable state of the bracket manager.

        Returns:
            Dict[str, Any]: The current state of brackets and categories.
        """
        return {
            "show_bracket": self.show_bracket,
            "active_category": self.active_category,
            "categories": self.categories,
            "active_match": self.active_match,
            "champion": self.champion
        }
