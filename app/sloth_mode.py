"""Opt-in Sloth Mode: background inbox review without automatic file moves."""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from . import config, organizer
from .scanner import safe_workspace_path, scan_folder, UnsafePath

DEFAULTS = {"enabled": False, "inbox": "inbox", "interval_minutes": 60, "last_run": None, "last_summary": None}

def _now():
    return datetime.now(timezone.utc).isoformat()

def settings():
    result = dict(DEFAULTS)
    with organizer._connect() as con:
        row = con.execute("SELECT value FROM preferences WHERE key='sloth_mode'").fetchone()
    if row:
        try:
            value = json.loads(row["value"])
            if isinstance(value, dict): result.update(value)
        except (ValueError, TypeError):
            pass
    return result

def configure(payload):
    current = settings()
    if "enabled" in payload:
        if not isinstance(payload["enabled"], bool): raise ValueError("enabled must be true or false.")
        current["enabled"] = payload["enabled"]
    if "inbox" in payload:
        inbox = str(payload["inbox"]).strip()
        if not inbox or Path(inbox).is_absolute() or ".." in Path(inbox).parts:
            raise ValueError("Inbox must be a relative folder inside the configured workspace.")
        safe_workspace_path(inbox)
        current["inbox"] = Path(inbox).as_posix()
    if "interval_minutes" in payload:
        try: interval = int(payload["interval_minutes"])
        except (ValueError, TypeError): raise ValueError("interval_minutes must be a whole number.")
        if interval < 15 or interval > 1440: raise ValueError("Schedule interval must be between 15 and 1440 minutes.")
        current["interval_minutes"] = interval
    with organizer._connect() as con:
        con.execute("INSERT INTO preferences(key,value,updated_at) VALUES('sloth_mode',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                    (json.dumps(current), _now()))
    return current

def run_once():
    prefs = settings()
    inbox = safe_workspace_path(prefs["inbox"])
    result = scan_folder(prefs["inbox"])
    paths = [f.relative_path for f in result["files"]]
    planned = organizer.build_plan(paths) if paths else {"ready_count": 0, "review_count": 0, "conflict_count": 0}
    # Sloth Mode deliberately prepares a report only. It never applies a plan.
    summary = {
        "ran_at": _now(), "inbox": prefs["inbox"], "files_seen": result["total_files"],
        "ready_for_review": planned["ready_count"], "needs_review": planned["review_count"],
        "conflicts": planned["conflict_count"], "files_changed": 0,
        "message": "Sloth Mode completed a review pass. No files were moved or deleted."
    }
    with organizer._connect() as con:
        row = con.execute("SELECT value FROM preferences WHERE key='sloth_mode'").fetchone()
        current = dict(DEFAULTS)
        if row:
            try: current.update(json.loads(row["value"]))
            except (ValueError, TypeError): pass
        current["last_run"] = summary["ran_at"]
        current["last_summary"] = summary
        con.execute("INSERT INTO preferences(key,value,updated_at) VALUES('sloth_mode',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                    (json.dumps(current), _now()))
    return summary

async def scheduler_loop(stop: asyncio.Event):
    """Periodic local review. Settings are re-read each cycle so disabling takes effect."""
    while not stop.is_set():
        prefs = settings()
        if prefs["enabled"]:
            try:
                await asyncio.to_thread(run_once)
            except Exception as exc:
                # Keep a short error summary; never log document contents.
                with organizer._connect() as con:
                    row = con.execute("SELECT value FROM preferences WHERE key='sloth_mode'").fetchone()
                    current = dict(DEFAULTS)
                    if row:
                        try: current.update(json.loads(row["value"]))
                        except (ValueError, TypeError): pass
                    current["last_summary"] = {"ran_at": _now(), "files_changed": 0, "error": str(exc)[:300],
                                               "message": "Sloth Mode could not complete the review pass. No files were changed."}
                    con.execute("INSERT INTO preferences(key,value,updated_at) VALUES('sloth_mode',?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                                (json.dumps(current), _now()))
        try:
            await asyncio.wait_for(stop.wait(), timeout=max(60, min(86400, int(prefs["interval_minutes"]) * 60)))
        except asyncio.TimeoutError:
            pass
