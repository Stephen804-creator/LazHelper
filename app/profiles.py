"""Local assistant profile preferences; never grants file capabilities."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from . import organizer, policies

ASSISTANT_PROFILES = {
    "general": {"label": "General assistant", "description": "Balanced help for understanding and organising a workspace.", "guidance": "Be clear, cautious, and concise. Separate evidence from assumptions."},
    "study": {"label": "Study assistant", "description": "Support learning, revision, and course material.", "guidance": "Explain concepts clearly, define technical terms, and favour structured study guidance without inventing facts."},
    "research": {"label": "Research assistant", "description": "Prioritise source evidence and uncertainty.", "guidance": "Distinguish source evidence from inference, identify missing evidence, and avoid unsupported claims."},
    "organiser": {"label": "Personal organiser", "description": "Prioritise calm, reversible file organisation.", "guidance": "Prefer explainable categories, reversible plans, collision checks, and explicit review before file changes."},
    "developer": {"label": "Developer assistant", "description": "Help understand code and project files safely.", "guidance": "Explain code and project structure. Never claim code was run or changed unless the application confirms it."},
    "custom": {"label": "Custom preferences", "description": "Use saved instructions when optional memory is enabled.", "guidance": "Follow applicable saved preferences while preserving application safety rules."},
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _connect():
    con = organizer._connect()
    con.execute("""CREATE TABLE IF NOT EXISTS assistant_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        profile TEXT NOT NULL DEFAULT 'general',
        memory_enabled INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    )""")
    con.commit()
    return con

def get_assistant_profile() -> dict[str, Any]:
    with _connect() as con:
        row = con.execute("SELECT profile,memory_enabled,updated_at FROM assistant_profile WHERE id=1").fetchone()
    name = row["profile"] if row and row["profile"] in ASSISTANT_PROFILES else "general"
    return {"profile": name, "memory_enabled": bool(row["memory_enabled"]) if row else False,
            "updated_at": row["updated_at"] if row else None, "profiles": ASSISTANT_PROFILES,
            "note": "Profiles guide recommendations only; they never grant permissions or approve changes."}

def update_assistant_profile(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) - {"profile", "memory_enabled"}:
        raise ValueError("Only profile and memory_enabled may be changed.")
    current = get_assistant_profile()
    name = payload.get("profile", current["profile"])
    enabled = payload.get("memory_enabled", current["memory_enabled"])
    if name not in ASSISTANT_PROFILES:
        raise ValueError("Choose a supported assistant profile.")
    if not isinstance(enabled, bool):
        raise ValueError("memory_enabled must be true or false.")
    with _connect() as con:
        con.execute("""INSERT INTO assistant_profile(id,profile,memory_enabled,updated_at) VALUES(1,?,?,?)
            ON CONFLICT(id) DO UPDATE SET profile=excluded.profile,memory_enabled=excluded.memory_enabled,updated_at=excluded.updated_at""",
            (name, int(enabled), _now()))
    return get_assistant_profile()

def instruction_context(relative_path: str = ".", task_type: str = "analysis") -> str:
    profile = get_assistant_profile()
    guidance = [ASSISTANT_PROFILES[profile["profile"]]["guidance"]]
    if profile["memory_enabled"]:
        normal_path = str(relative_path or ".").replace("\\", "/").strip("/")
        for row in policies.list_instructions()[:50]:
            if not row.get("enabled"):
                continue
            scope, scope_path = row.get("scope"), row.get("scope_path", "")
            applies = scope == "global"
            if scope == "folder":
                applies = normal_path == scope_path or normal_path.startswith(scope_path.rstrip("/") + "/")
            elif scope == "task":
                applies = scope_path in {task_type, "general"}
            if applies:
                guidance.append(str(row.get("instruction", ""))[:1000])
            if len(guidance) >= 8:
                break
    return "\n".join(guidance)[:4000]
