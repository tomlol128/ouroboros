"""
Supervisor — Web API server.

Provides HTTP REST + WebSocket endpoints for the web interface.
- GET  /api/status      — current state snapshot (JSON)
- GET  /api/identity    — identity.md content
- GET  /api/chat        — last N messages from chat.jsonl
- POST /api/chat        — send a message (injected as owner message)
- WS   /ws              — real-time feed (messages, progress, status updates)

CORS is open (GitHub Pages → Colab tunnel).
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import pathlib
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

log = logging.getLogger(__name__)

try:
    from aiohttp import web
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    web = None  # type: ignore
    aiohttp = None  # type: ignore


# ---------------------------------------------------------------------------
# Module-level state (set via init())
# ---------------------------------------------------------------------------
_DRIVE_ROOT: Optional[pathlib.Path] = None
_REPO_DIR: Optional[pathlib.Path] = None
_SEND_MESSAGE_CB: Optional[Callable[[str], None]] = None
_app: Optional[Any] = None
_runner: Optional[Any] = None
_site: Optional[Any] = None
_ws_clients: Set[Any] = set()
_event_buffer: List[str] = []  # last 100 serialized events for new connections
MAX_BUFFER = 100
PORT = 7860


def init(
    drive_root: pathlib.Path,
    repo_dir: pathlib.Path,
    send_message_cb: Callable[[str], None],
    port: int = 7860,
) -> None:
    global _DRIVE_ROOT, _REPO_DIR, _SEND_MESSAGE_CB, PORT
    _DRIVE_ROOT = drive_root
    _REPO_DIR = repo_dir
    _SEND_MESSAGE_CB = send_message_cb
    PORT = port


# ---------------------------------------------------------------------------
# WebSocket broadcast (called from sync context via asyncio.run_coroutine_threadsafe)
# ---------------------------------------------------------------------------

_loop: Optional[asyncio.AbstractEventLoop] = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def broadcast(event_type: str, data: Any) -> None:
    """Broadcast a message to all connected WebSocket clients (thread-safe, fire-and-forget)."""
    msg = json.dumps({
        "type": event_type,
        "data": data,
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, ensure_ascii=False)

    # Buffer for late-joining clients
    _event_buffer.append(msg)
    if len(_event_buffer) > MAX_BUFFER:
        _event_buffer.pop(0)

    if not _ws_clients:
        return

    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast_async(msg), _loop)


async def _broadcast_async(msg: str) -> None:
    dead = set()
    for ws in list(_ws_clients):
        try:
            if not ws.closed:
                await ws.send_str(msg)
            else:
                dead.add(ws)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

async def _cors_middleware(app: Any, handler: Any) -> Any:
    async def middleware(request: Any) -> Any:
        if request.method == "OPTIONS":
            response = web.Response(status=200)
        else:
            try:
                response = await handler(request)
            except web.HTTPException as e:
                response = e
            except Exception as e:
                log.warning("WebServer handler error: %s", e, exc_info=True)
                response = web.Response(
                    status=500,
                    text=json.dumps({"error": str(e)}),
                    content_type="application/json",
                )
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
    return middleware


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read_version() -> str:
    try:
        if _REPO_DIR:
            vpath = _REPO_DIR / "VERSION"
            if vpath.exists():
                return vpath.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "unknown"


def _load_state_safe() -> Dict[str, Any]:
    try:
        from supervisor.state import load_state
        return load_state()
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def _handle_health(request: Any) -> Any:
    return web.Response(
        text=json.dumps({"ok": True, "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}),
        content_type="application/json",
    )


async def _handle_status(request: Any) -> Any:
    try:
        st = _load_state_safe()
        total_budget = float(os.environ.get("OUROBOROS_TOTAL_BUDGET", "10"))
        try:
            from supervisor.state import TOTAL_BUDGET_LIMIT
            if TOTAL_BUDGET_LIMIT > 0:
                total_budget = float(TOTAL_BUDGET_LIMIT)
        except Exception:
            pass

        spent = float(st.get("spent_usd") or 0.0)
        status = {
            "version": _read_version(),
            "spent_usd": round(spent, 4),
            "budget_usd": total_budget,
            "remaining_usd": round(max(0.0, total_budget - spent), 4),
            "budget_pct": round(spent / total_budget * 100, 1) if total_budget > 0 else 0,
            "spent_calls": int(st.get("spent_calls") or 0),
            "evolution_mode": bool(st.get("evolution_mode_enabled")),
            "evolution_cycle": int(st.get("evolution_cycle") or 0),
            "current_sha": str(st.get("current_sha") or "")[:8],
            "current_branch": str(st.get("current_branch") or ""),
            "session_id": str(st.get("session_id") or ""),
            "model": os.environ.get("OUROBOROS_MODEL", "unknown"),
            "online": True,
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return web.Response(
            text=json.dumps(status, ensure_ascii=False),
            content_type="application/json",
        )
    except Exception as e:
        return web.Response(
            status=500,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )


async def _handle_identity(request: Any) -> Any:
    try:
        if _DRIVE_ROOT:
            path = _DRIVE_ROOT / "memory" / "identity.md"
            content = path.read_text(encoding="utf-8") if path.exists() else "# Identity not found"
        else:
            content = "# Drive not mounted"
        return web.Response(
            text=json.dumps({"content": content}, ensure_ascii=False),
            content_type="application/json",
        )
    except Exception as e:
        return web.Response(
            status=500,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )


async def _handle_chat_get(request: Any) -> Any:
    try:
        n = min(int(request.rel_url.query.get("n", "50")), 200)
        messages: List[Dict[str, Any]] = []
        if _DRIVE_ROOT:
            path = _DRIVE_ROOT / "logs" / "chat.jsonl"
            if path.exists():
                for line in path.read_text(encoding="utf-8").strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        messages.append(json.loads(line))
                    except Exception:
                        pass
        return web.Response(
            text=json.dumps({"messages": messages[-n:]}, ensure_ascii=False),
            content_type="application/json",
        )
    except Exception as e:
        return web.Response(
            status=500,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )


async def _handle_chat_post(request: Any) -> Any:
    try:
        body = await request.json()
        text = str(body.get("text") or "").strip()
        if not text:
            return web.Response(
                status=400,
                text=json.dumps({"error": "empty text"}),
                content_type="application/json",
            )
        if _SEND_MESSAGE_CB:
            _SEND_MESSAGE_CB(text)
        msg_id = uuid.uuid4().hex[:8]
        broadcast("user_message", {
            "text": text,
            "role": "user",
            "id": msg_id,
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        return web.Response(
            text=json.dumps({"ok": True, "id": msg_id}),
            content_type="application/json",
        )
    except Exception as e:
        return web.Response(
            status=500,
            text=json.dumps({"error": str(e)}),
            content_type="application/json",
        )


async def _handle_ws(request: Any) -> Any:
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    _ws_clients.add(ws)
    log.info("WebSocket connected. Clients: %d", len(_ws_clients))

    try:
        # Replay recent events
        for msg in list(_event_buffer[-30:]):
            if not ws.closed:
                await ws.send_str(msg)

        # Send current status immediately
        try:
            st = _load_state_safe()
            await ws.send_str(json.dumps({
                "type": "status",
                "data": {
                    "online": True,
                    "version": _read_version(),
                    "model": os.environ.get("OUROBOROS_MODEL", "unknown"),
                    "spent_usd": round(float(st.get("spent_usd") or 0.0), 4),
                    "spent_calls": int(st.get("spent_calls") or 0),
                },
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }))
        except Exception:
            pass

        # Message loop
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:  # type: ignore
                try:
                    data = json.loads(msg.data)
                    msg_type = str(data.get("type") or "")
                    if msg_type == "ping":
                        await ws.send_str(json.dumps({"type": "pong"}))
                    elif msg_type == "message":
                        text = str(data.get("text") or "").strip()
                        if text and _SEND_MESSAGE_CB:
                            _SEND_MESSAGE_CB(text)
                            broadcast("user_message", {
                                "text": text,
                                "role": "user",
                                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            })
                except Exception as e:
                    log.debug("WS parse error: %s", e)
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):  # type: ignore
                break

    except Exception as e:
        log.debug("WebSocket error: %s", e)
    finally:
        _ws_clients.discard(ws)
        log.info("WebSocket disconnected. Clients: %d", len(_ws_clients))

    return ws


async def _handle_options(request: Any) -> Any:
    return web.Response(status=200)


# ---------------------------------------------------------------------------
# App + lifecycle
# ---------------------------------------------------------------------------

def create_app() -> Any:
    if not AIOHTTP_AVAILABLE:
        raise RuntimeError("aiohttp not installed. Run: pip install aiohttp")
    app = web.Application(middlewares=[_cors_middleware])
    app.router.add_get("/health", _handle_health)
    app.router.add_get("/api/status", _handle_status)
    app.router.add_get("/api/identity", _handle_identity)
    app.router.add_get("/api/chat", _handle_chat_get)
    app.router.add_post("/api/chat", _handle_chat_post)
    app.router.add_get("/ws", _handle_ws)
    app.router.add_options("/{path_info:.*}", _handle_options)
    return app


async def start_server(port: int = None) -> int:
    global _app, _runner, _site
    if not AIOHTTP_AVAILABLE:
        raise RuntimeError("aiohttp not installed")

    p = port or PORT
    _app = create_app()
    _runner = web.AppRunner(_app)
    await _runner.setup()
    _site = web.TCPSite(_runner, "0.0.0.0", p)
    await _site.start()
    log.info("WebServer started on 0.0.0.0:%d", p)
    return p


async def stop_server() -> None:
    global _runner, _site
    if _site:
        await _site.stop()
        _site = None
    if _runner:
        await _runner.cleanup()
        _runner = None


def is_running() -> bool:
    return _site is not None
