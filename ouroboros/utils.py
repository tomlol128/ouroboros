import logging
import os
import pathlib
from typing import Optional
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


def safe_relpath(path: pathlib.Path, base: pathlib.Path) -> pathlib.Path:
    """Safely calculate relative path without going above base directory."""
    try:
        return path.relative_to(base)
    except ValueError:
        # If path is not under base, return absolute path to avoid security issues
        return path


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def read_text(path: pathlib.Path) -> str:
    """Read UTF-8 text file."""
    return path.read_text(encoding="utf-8")


def write_text(path: pathlib.Path, content: str) -> None:
    """Write UTF-8 text file."""
    path.write_text(content, encoding="utf-8")


def append_jsonl(path: pathlib.Path, data: dict) -> None:
    """Append JSON object to .jsonl file."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")


def clip_text(text: str, max_len: int) -> str:
    """Truncate text to max_len while attempting to preserve sentences."""
    if len(text) <= max_len:
        return text
    # Try to cut at sentence boundary
    cut = text.rfind('. ', 0, max_len)
    if cut > 0:
        return text[:cut+1]
    return text[:max_len] + "..."


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