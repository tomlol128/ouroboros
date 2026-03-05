import logging
import os
import re
import json
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class PathTraversalError(Exception):
    pass

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def sanitize_input(text: str) -> str:
    """Safely clean user input by removing control characters and trimming"""
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    return text.strip()

def safe_relpath(path: str, base: str = '/app') -> str:
    """Safely extract relative path within base directory"""
    base = os.path.abspath(base)
    target = os.path.abspath(os.path.join(base, path))
    if os.path.commonpath([base, target]) != base:
        raise PathTraversalError(f"Path '{path}' is outside base directory '{base}'")
    return os.path.relpath(target, base)

def read_text(path: str) -> str:
    """Read text file with UTF-8 encoding"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_text(path: str, content: str, mode: str = 'w') -> None:
    """Write text file with UTF-8 encoding"""
    with open(path, mode, encoding='utf-8') as f:
        f.write(content)

def run_cmd(cmd: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Run shell command and capture output"""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {
        'exit_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr
    }

def append_jsonl(path: str, data: Dict) -> None:
    """Append JSON object to .jsonl file"""
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data) + '\n')

def truncate_for_log(s: str, max_len: int = 200) -> str:
    """Truncate string for logging with preservation of structure"""
    return (s[:max_len] + '...') if len(s) > max_len else s

def short(s: str, n: int = 50) -> str:
    """Shorten string with ellipsis"""
    return s[:n] + '...' if len(s) > n else s

def clip_text(text: str, max_len: int = 200) -> str:
    """Alias for truncate_for_log"""
    return truncate_for_log(text, max_len)

def estimate_tokens(text: str) -> int:
    """Rough token estimation (simplified)"""
    return max(1, len(text) // 4)