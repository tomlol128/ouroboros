import logging
import os
import pathlib
import subprocess
import hashlib
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
import json


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for the given module name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
    return logger


def safe_relpath(path: Union[str, pathlib.Path], base: Optional[Union[str, pathlib.Path]] = None) -> str:
    """Safely calculate relative path with normalized path separators and no leading slashes."""
    path_obj = pathlib.Path(path).resolve()
    base_obj = pathlib.Path(base).resolve() if base else pathlib.Path.cwd().resolve()

    try:
        rel = path_obj.relative_to(base_obj)
        # Convert to string, normalize path separators, and strip leading slashes/dots
        return str(rel).replace('\\', '/').lstrip('./\\')
    except ValueError:
        raise ValueError(f"Path '{path}' is outside base directory '{base_obj}'")

def run_cmd(cmd: List[str], cwd: Optional[str] = None) -> str:
    """Run shell command and return stdout."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout


def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 chars in English)."""
    return max(1, len(text) // 4)


def get_git_info(repo_path: str) -> Dict[str, str]:
    """Get current git branch and SHA."""
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_path).strip().decode()
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_path).strip().decode()
        return {'sha': sha, 'branch': branch}
    except Exception as e:
        return {'error': str(e)}

def short(s: str, length: int = 7) -> str:
    """Create short hash of string."""
    return hashlib.sha256(s.encode()).hexdigest()[:length]


def sanitize_task_for_event(task: dict) -> dict:
    """Sanitize task data for event logging."""
    if "content" in task:
        task["content"] = "<redacted>"
    if "prompt" in task:
        task["prompt"] = clip_text(task["prompt"], 200)
    return task


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Union[str, pathlib.Path]) -> str:
    """Read UTF-8 text file."""
    return pathlib.Path(path).read_text(encoding="utf-8")


def write_text(path: Union[str, pathlib.Path], content: str) -> None:
    """Write UTF-8 text file."""
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(content, encoding="utf-8")


def append_jsonl(path: Union[str, pathlib.Path], data: dict) -> None:
    """Append JSON object to .jsonl file."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")


def clip_text(text: str, max_len: int) -> str:
    """Truncate text to max_len while attempting to preserve sentences."""
    if len(text) <= max_len:
        return text
    # Try to cut at sentence boundary
    cut = text.rfind('. ', 0, max_len)
    if cut > 0:
        return text[:cut+1]
    return text[:max_len] + '...(truncated)...'


def sanitize_tool_args_for_log(args: dict) -> dict:
    """Remove sensitive data from tool args for logging."""
    if "content" in args:
        args["content"] = "<redacted>"
    if "token" in args:
        args["token"] = "<redacted>"
    return args


def sanitize_tool_result_for_log(result: str) -> str:
    """Redact sensitive info from tool results."""
    # Example: hide API keys
    return result.replace("sk-or-v1-", "sk-or-v1-<redacted>")


def truncate_for_log(s: str, max_len: int = 500) -> str:
    """Truncate string for log display."""
    return s[:max_len] + ("..." if len(s) > max_len else "")