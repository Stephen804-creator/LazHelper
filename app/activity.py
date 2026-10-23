"""Real API activity history and in-flight request visibility."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from . import organizer

_active: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def begin(method: str, path: str) -> str | None:
    if not path.startswith("/api/") or path == "/api/activity":
        return None
    token = uuid.uuid4().hex
    _active[token] = {
        "id": token, "method": method, "path": path, "started_at": _now(),
        "started_clock": time.monotonic(), "status": "running",
    }
    return token


def finish(token: str | None, status_code: int) -> None:
    if not token:
        return
    row = _active.pop(token, None)
    if not row:
        return
    duration = max(0, round((time.monotonic() - row["started_clock"]) * 1000))
    with organizer._connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            duration_ms INTEGER NOT NULL
        )""")
        con.execute(
            "INSERT INTO activity_events(method,path,status_code,started_at,completed_at,duration_ms) "
            "VALUES(?,?,?,?,?,?)",
            (row["method"], row["path"], int(status_code), row["started_at"], _now(), duration),
        )
        con.execute("DELETE FROM activity_events WHERE id NOT IN "
                    "(SELECT id FROM activity_events ORDER BY id DESC LIMIT 500)")
    row.pop("started_clock", None)
    row["status_code"] = int(status_code)
    row["duration_ms"] = duration


def history(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    with organizer._connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            duration_ms INTEGER NOT NULL
        )""")
        rows = con.execute(
            "SELECT id,method,path,status_code,started_at,completed_at,duration_ms "
            "FROM activity_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    active = [{
        "id": row["id"], "method": row["method"], "path": row["path"],
        "started_at": row["started_at"], "status": "running",
    } for row in list(_active.values())]
    active.sort(key=lambda item: item["started_at"])
    return {
        "active": active,
        "events": [dict(row) for row in rows],
        "count": len(rows),
        "retention_limit": 500,
        "privacy": "Request paths only; prompts, document contents, and request bodies are not recorded.",
    }
