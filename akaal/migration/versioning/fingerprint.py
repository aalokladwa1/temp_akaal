import hashlib
import re

class FingerprintEngine:
    """
    Computes deterministic structural hashes (fingerprints) of database schema DDLs.
    Ignores whitespace, formatting, comments, and cosmetic dialect differences.
    """
    @staticmethod
    def generate_fingerprint(ddl: str) -> str:
        # 1. Remove multi-line comments /* ... */
        cleaned = re.sub(r"/\*.*?\*/", "", ddl, flags=re.DOTALL)
        
        # 2. Remove single-line comments -- ...
        cleaned = re.sub(r"--.*?\n", "\n", cleaned)
        
        # 3. Collapse duplicate whitespace / tabs / newlines to single spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        # 4. Standardize quotes: strip square brackets, double quotes, and single quotes
        cleaned = cleaned.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
        
        # 5. Case-insensitivity: convert unquoted keywords/identifiers to lowercase
        # For simplicity, convert the entire normalized string to lowercase
        cleaned = cleaned.lower()
        
        # 6. Lexicographical sorting of comma-separated components inside parentheses
        # e.g., column lists or index lists: (id INT, name VARCHAR) -> (id INT, name VARCHAR) sorted
        # Find matching outer parentheses content and sort items inside
        matches = re.findall(r"\((.*?)\)", cleaned)
        for match in matches:
            parts = [p.strip() for p in match.split(",") if p.strip()]
            sorted_parts = sorted(parts)
            sorted_match = ", ".join(sorted_parts)
            cleaned = cleaned.replace(match, sorted_match)
            
        # 7. Generate deterministic SHA-256 hash
        hasher = hashlib.sha256()
        hasher.update(cleaned.encode("utf-8"))
        return hasher.hexdigest()
