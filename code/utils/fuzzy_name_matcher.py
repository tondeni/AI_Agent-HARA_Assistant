# ==============================================================================
# code/utils/fuzzy_name_matcher.py
# Intelligent fuzzy matching for automotive system names
# ==============================================================================

from typing import List, Tuple, Optional, Dict
from cat.log import log
import re
import json
import os

class FuzzyNameMatcher:
    """
    Intelligent fuzzy matching for automotive system names.
    
    Features:
    - Abbreviation expansion (BMS → Battery Management System)
    - Common variations (Wiper vs Wiper and Washer System)
    - Fuzzy string matching with configurable threshold
    - Case-insensitive matching
    - Special character normalization
    
    Examples:
        matcher.match("BMS", ["Battery_Management_System.txt"])
        → ("Battery_Management_System.txt", 95.0)
        
        matcher.match("Wiper", ["Windscreen_Wiper_and_Washer_System.txt"])
        → ("Windscreen_Wiper_and_Washer_System.txt", 88.0)
    """
    
    def __init__(self, config_path: Optional[str] = None, threshold: float = 75.0):
        """
        Initialize fuzzy matcher.
        
        Args:
            config_path: Path to system_aliases.json (optional)
            threshold: Minimum similarity score (0-100) for matches
        """
        self.threshold = threshold
        self.aliases = {}
        
        # Try to import rapidfuzz
        try:
            from rapidfuzz import fuzz, process
            self.fuzz = fuzz
            self.process = process
            self.fuzzy_available = True
            log.info("✅ Fuzzy matching enabled (rapidfuzz)")
        except ImportError:
            log.warning("⚠️ rapidfuzz not installed - fuzzy matching limited")
            self.fuzzy_available = False
        
        # Load aliases configuration
        if config_path and os.path.exists(config_path):
            self._load_aliases(config_path)
    
    def _load_aliases(self, config_path: str):
        """Load system name aliases from JSON config."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.aliases = json.load(f)
            log.info(f"✅ Loaded {len(self.aliases)} system aliases")
        except Exception as e:
            log.warning(f"Could not load aliases: {e}")
    
    def match(
        self, 
        query: str, 
        candidates: List[str], 
        return_all: bool = False
    ) -> Optional[Tuple[str, float]] | List[Tuple[str, float]]:
        """
        Find best matching filename for a system name query.
        
        Args:
            query: System name to search for (e.g., "BMS", "Wiper")
            candidates: List of filenames to search
            return_all: If True, return all matches above threshold
        
        Returns:
            - If return_all=False: (best_match, score) or None
            - If return_all=True: [(match, score), ...] sorted by score
        
        Examples:
            >>> matcher.match("BMS", ["Battery_Management_System.txt"])
            ("Battery_Management_System.txt", 95.0)
            
            >>> matcher.match("Wiper", ["Wiper_System.txt", "Washer_System.txt"])
            ("Wiper_System.txt", 100.0)
        """
        
        if not candidates:
            return [] if return_all else None
        
        # Normalize query
        normalized_query = self._normalize_name(query)
        
        # Check for exact alias match first
        expanded_query = self._expand_alias(normalized_query)
        
        # Score all candidates
        scored_matches = []
        
        for candidate in candidates:
            # Extract name from filename
            candidate_name = self._extract_name_from_filename(candidate)
            normalized_candidate = self._normalize_name(candidate_name)
            
            # Calculate match score
            score = self._calculate_match_score(
                query=normalized_query,
                expanded_query=expanded_query,
                candidate=normalized_candidate
            )
            
            if score >= self.threshold:
                scored_matches.append((candidate, score))
        
        # Sort by score (descending)
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        
        if return_all:
            return scored_matches
        else:
            return scored_matches[0] if scored_matches else None
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize system name for comparison.
        
        - Lowercase
        - Remove special characters
        - Replace underscores/hyphens with spaces
        - Remove extra whitespace
        """
        name = name.lower()
        name = re.sub(r'[_\-]', ' ', name)  # Replace _ and - with space
        name = re.sub(r'[^\w\s]', '', name)  # Remove special chars
        name = re.sub(r'\s+', ' ', name).strip()  # Normalize whitespace
        return name
    
    def _extract_name_from_filename(self, filename: str) -> str:
        """Extract system name from filename (remove extension)."""
        # Remove file extension
        name = os.path.splitext(filename)[0]
        return name
    
    def _expand_alias(self, query: str) -> Optional[str]:
        """
        Expand abbreviations using alias dictionary.
        
        Examples:
            "bms" → "battery management system"
            "esc" → "electronic stability control"
        """
        # Check if query exactly matches an alias
        if query in self.aliases:
            expanded = self.aliases[query]
            log.info(f"🔄 Alias expansion: '{query}' → '{expanded}'")
            return self._normalize_name(expanded)
        
        # Check if any alias keyword matches
        for alias, full_name in self.aliases.items():
            if alias in query or query in alias:
                return self._normalize_name(full_name)
        
        return None
    
    def _calculate_match_score(
        self, 
        query: str, 
        expanded_query: Optional[str],
        candidate: str
    ) -> float:
        """
        Calculate match score between query and candidate.
        
        Uses multiple scoring methods:
        1. Exact match (100)
        2. Starts with query (95)
        3. Contains all query words (90)
        4. Fuzzy ratio (if available)
        5. Partial fuzzy ratio (if available)
        
        Returns best score.
        """
        scores = []
        
        # Method 1: Exact match
        if query == candidate:
            return 100.0
        
        # Method 2: Check expanded alias
        if expanded_query and expanded_query == candidate:
            return 98.0
        
        # Method 3: Starts with query
        if candidate.startswith(query):
            scores.append(95.0)
        
        if expanded_query and candidate.startswith(expanded_query):
            scores.append(96.0)
        
        # Method 4: Contains all query words
        query_words = set(query.split())
        candidate_words = set(candidate.split())
        
        if query_words.issubset(candidate_words):
            # Score based on ratio of matched words
            word_ratio = len(query_words) / len(candidate_words)
            scores.append(85.0 + (word_ratio * 10))
        
        # Method 5: Fuzzy matching (if available)
        if self.fuzzy_available:
            # Token set ratio (best for reordered words)
            token_score = self.fuzz.token_set_ratio(query, candidate)
            scores.append(token_score)
            
            # Partial ratio (substring matching)
            partial_score = self.fuzz.partial_ratio(query, candidate)
            scores.append(partial_score * 0.9)  # Weight partial matches lower
            
            # Check expanded query
            if expanded_query:
                expanded_token_score = self.fuzz.token_set_ratio(expanded_query, candidate)
                scores.append(expanded_token_score)
        
        # Return best score
        return max(scores) if scores else 0.0
    
    def add_alias(self, abbreviation: str, full_name: str):
        """
        Add a system name alias at runtime.
        
        Args:
            abbreviation: Short form (e.g., "BMS", "ESC")
            full_name: Full system name
        
        Example:
            matcher.add_alias("BMS", "Battery Management System")
        """
        normalized_abbr = self._normalize_name(abbreviation)
        self.aliases[normalized_abbr] = full_name
        log.info(f"✅ Added alias: {abbreviation} → {full_name}")
    
    def get_all_matches_above_threshold(
        self, 
        query: str, 
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Get all candidates matching above threshold, sorted by score.
        
        Useful for debugging or showing multiple options to user.
        """
        return self.match(query, candidates, return_all=True) or []


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def create_default_aliases() -> Dict[str, str]:
    """
    Create default automotive system aliases.
    
    Returns dictionary of common abbreviations to full names.
    """
    return {
        # Powertrain & Energy
        "bms": "Battery Management System",
        "ems": "Engine Management System",
        "tms": "Thermal Management System",
        "pms": "Power Management System",
        
        # Chassis & Dynamics
        "abs": "Anti-lock Braking System",
        "esc": "Electronic Stability Control",
        "esp": "Electronic Stability Program",
        "tcs": "Traction Control System",
        "ebd": "Electronic Brake-force Distribution",
        "eba": "Emergency Brake Assist",
        
        # Steering
        "eps": "Electric Power Steering",
        "pas": "Power Assisted Steering",
        
        # Safety Systems
        "srs": "Supplemental Restraint System",
        "airbag": "Airbag Control System",
        "abs": "Anti-lock Braking System",
        
        # ADAS
        "acc": "Adaptive Cruise Control",
        "lka": "Lane Keeping Assist",
        "ldw": "Lane Departure Warning",
        "aeb": "Autonomous Emergency Braking",
        "bsd": "Blind Spot Detection",
        "fcw": "Forward Collision Warning",
        
        # Lighting
        "afs": "Adaptive Front-lighting System",
        "drl": "Daytime Running Lights",
        
        # Body & Comfort
        "hvac": "Heating Ventilation Air Conditioning",
        "bcm": "Body Control Module",
        "peps": "Passive Entry Passive Start",
        "rke": "Remote Keyless Entry",
        
        # Common variations
        "wiper": "Windscreen Wiper and Washer System",
        "washer": "Windscreen Wiper and Washer System",
        "brake": "Braking System",
        "braking": "Braking System",
        "steering": "Steering Control System",
        "battery": "Battery Management System",
        "airbag": "Airbag Control System",
    }


def save_aliases_to_file(aliases: Dict[str, str], filepath: str):
    """Save aliases dictionary to JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(aliases, f, indent=2, sort_keys=True)
        log.info(f"✅ Saved aliases to: {filepath}")
    except Exception as e:
        log.error(f"❌ Could not save aliases: {e}")


# ==============================================================================
# USAGE EXAMPLES (for testing)
# ==============================================================================

if __name__ == "__main__":
    # Example usage
    matcher = FuzzyNameMatcher(threshold=70.0)
    
    # Add default aliases
    for abbr, full in create_default_aliases().items():
        matcher.add_alias(abbr, full)
    
    # Test cases
    test_files = [
        "Battery_Management_System.txt",
        "Windscreen_Wiper_and_Washer_System.txt",
        "Electronic_Stability_Control.txt",
        "Adaptive_Cruise_Control.docx",
        "Brake_System_Definition.pdf"
    ]
    
    test_queries = [
        "BMS",
        "bms",
        "Battery",
        "Wiper",
        "Washer",
        "ESC",
        "stability",
        "ACC",
        "Brake"
    ]
    
    print("\n" + "="*70)
    print("FUZZY NAME MATCHER - TEST RESULTS")
    print("="*70)
    
    for query in test_queries:
        result = matcher.match(query, test_files)
        if result:
            filename, score = result
            print(f"\n Query: '{query}'")
            print(f"   → Match: {filename}")
            print(f"   → Score: {score:.1f}%")
        else:
            print(f"\n Query: '{query}'")
            print(f"   → No match found")