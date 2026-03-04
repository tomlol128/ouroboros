"""
Supervisor — Tunnel management.

Uses cloudflared to expose the local web server via a public HTTPS URL.
Writes the URL to Drive state and commits it to docs/api_url.json so
the GitHub Pages frontend can discover the live endpoint.
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
import select
import subprocess
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)

_DRIVE_ROOT: Optional[pathlib.Path] = None
_REPO_DIR: Optional[pathlib.Path] = None
_PUBLIC_URL: Optional[str] = None
_tunnel_proc: Optional[subprocess.Popen] = None
_URL_FILE_NAME = "web_url.json"


def init(drive_root: pathlib.Path, repo_dir: pathlib.Path) -> None:
    global _DRIVE_ROOT, _REPO_DIR
    _DRIVE_ROOT = drive_root
    _REPO_DIR = repo_dir


def get_public_url() -> Optional[str]:
    return _PUBLIC_URL


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def _install_cloudflared() -> bool:
    """Install cloudflared if not already present."""
    try:
        result = subprocess.run(
            ["which", "cloudflared"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    try:
        log.info("Installing cloudflared...")
        subprocess.run(
            [
                "bash", "-c",
                "wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/"
                "cloudflared-linux-amd64 -O /usr/local/bin/cloudflared "
                "&& chmod +x /usr/local/bin/cloudflared",
            ],
            check=True,
            timeout=120,
        )
        return True
    except Exception as e:
        log.warning("cloudflared install failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------

def _extract_url(line: str) -> Optional[str]:
    """Extract a public HTTPS URL from a cloudflared log line."""
    patterns = [
        r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com",
        r"https://[a-zA-Z0-9\-]+\.cloudflare\.com",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(0).strip().rstrip("/")
    return None


# ---------------------------------------------------------------------------
# Persist URL
# ---------------------------------------------------------------------------

def _save_url(url: str) -> None:
    global _PUBLIC_URL
    _PUBLIC_URL = url
    data = {
        "url": url,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "online",
    }
    payload = json.dumps(data, indent=2)

    # Write to Drive
    if _DRIVE_ROOT:
        try:
            p = _DRIVE_ROOT / "state" / _URL_FILE_NAME
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(payload, encoding="utf-8")
        except Exception as e:
            log.warning("Could not save URL to Drive: %s", e)

    # Commit to repo docs/ for GitHub Pages
    if _REPO_DIR:
        try:
            docs_p = _REPO_DIR / "docs" / "api_url.json"
            docs_p.write_text(payload, encoding="utf-8")
            subprocess.run(["git", "add", "docs/api_url.json"], cwd=str(_REPO_DIR), check=True)
            subprocess.run(
                ["git", "commit", "-m", f"web: live API URL → {url[:50]}"],
                cwd=str(_REPO_DIR),
                check=False,
            )
            subprocess.run(
                ["git", "push", "origin", "ouroboros"],
                cwd=str(_REPO_DIR),
                check=False,
            )
            log.info("URL committed to repo: %s", url)
        except Exception as e:
            log.warning("Could not commit URL to repo: %s", e)


def _clear_url() -> None:
    global _PUBLIC_URL
    _PUBLIC_URL = None
    data = {
        "url": None,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "offline",
    }
    if _DRIVE_ROOT:
        try:
            p = _DRIVE_ROOT / "state" / _URL_FILE_NAME
            p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------

def start_tunnel(port: int = 7860, timeout: int = 90) -> Optional[str]:
    """Start cloudflared tunnel. Returns public URL or None."""
    global _tunnel_proc

    if not _install_cloudflared():
        return _try_ngrok(port, timeout)

    try:
        _tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        deadline = time.time() + timeout
        buffer = ""

        while time.time() < deadline:
            if _tunnel_proc.poll() is not None:
                log.warning("cloudflared exited unexpectedly. Output: %s", buffer[-500:])
                break

            ready, _, _ = select.select([_tunnel_proc.stdout], [], [], 1.0)
            if ready:
                line = _tunnel_proc.stdout.readline()
                if not line:
                    break
                buffer += line
                log.debug("cloudflared | %s", line.rstrip())
                url = _extract_url(line)
                if url:
                    log.info("Tunnel URL obtained: %s", url)
                    _save_url(url)
                    # Drain stdout in background so buffer doesn't fill
                    def _drain(proc: subprocess.Popen) -> None:
                        try:
                            for _ in proc.stdout:
                                pass
                        except Exception:
                            pass
                    threading.Thread(target=_drain, args=(_tunnel_proc,), daemon=True).start()
                    return url

        log.warning("Timed out waiting for tunnel URL")
        return None

    except Exception as e:
        log.warning("cloudflared failed: %s", e)
        return None


def _try_ngrok(port: int, timeout: int) -> Optional[str]:
    """Fallback: try pyngrok if cloudflared isn't available."""
    try:
        from pyngrok import ngrok  # type: ignore
        tunnel = ngrok.connect(port, "http")
        url = str(tunnel.public_url)
        if url.startswith("http://"):
            url = "https://" + url[7:]
        _save_url(url)
        log.info("ngrok URL: %s", url)
        return url
    except Exception as e:
        log.warning("ngrok fallback failed: %s", e)
        return None


def stop_tunnel() -> None:
    """Stop the running tunnel."""
    global _tunnel_proc
    if _tunnel_proc:
        try:
            _tunnel_proc.terminate()
            _tunnel_proc.wait(timeout=5)
        except Exception:
            pass
        _tunnel_proc = None
    _clear_url()
