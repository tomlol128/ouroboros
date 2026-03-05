import os
import re
from typing import Optional
from ouroboros.exceptions import PathTraversalError


def sanitize_input(text: str) -> str:
    """Safely clean user input by removing control characters and trimming"""
    # Remove control characters but preserve newlines/spaces
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    return text.strip()

def safe_relpath(path: str, base: str = '/app') -> str:
    """Safely extract relative path within base directory"""
    # Normalize paths to absolute form for comparison
    base = os.path.abspath(base)
    target = os.path.abspath(os.path.join(base, path))

    # Check containment using common prefix
    if os.path.commonpath([base, target]) != base:
        raise PathTraversalError(f"Path '{path}' is outside base directory '{base}'")

    return os.path.relpath(target, base)

class PathTraversalError(Exception):
    pass
