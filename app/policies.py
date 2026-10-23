"""Owner-controlled capabilities and reusable instruction policies.

This module stores policy in the existing local SQLite state database. It is not an
authentication system: run the local app only for trusted users. Permissions constrain
what the application API may do inside the configured workspace.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from . import organizer

CAPABILITIES = {
    "read_metadata": "Read file names, paths, sizes, and timestamps",
    "read_content": "Extract and search file contents",
    "create_files": "Create new files",
    "create_folders": "Create folders",
    "edit_files": "Edit existing files",
    "rename_files": "Rename files",
    "move_files": "Move files after explicit approval",
    "copy_files": "Copy files",
    "export_files": "Export file contents or batches",
    "restore_moves": "Undo a previous move",
    "delete_files": "Delete files",
    "run_commands": "Execute shell commands or programs",
}
DEFAULT_POLICY = {key: False for key in CAPABILITIES}
DEFAULT_POLICY.update({
    "read_metadata": True,
    "read_content": True,
    "mode": "preview",
    "scope": "configured_workspace",
})
VALID_MODES = {"preview", "ask_before_changes", "authorised_automation"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    con = organizer._connect()
    con.execute("""CREATE TABLE IF NOT EXISTS owner_policy (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS owner_instructions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope TEXT NOT NULL,
        scope_path TEXT NOT NULL DEFAULT '',
        instruction TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    con.commit()
    return con


def get_policy() -> dict[str, Any]:
    with _connect() as con:
        row = con.execute("SELECT value FROM owner_policy WHERE id=1").fetchone()
    result = dict(DEFAULT_POLICY)
    if row:
        try:
            saved = json.loads(row["value"])
            if isinstance(saved, dict):
                for key in DEFAULT_POLICY:
                    if key in saved and (isinstance(DEFAULT_POLICY[key], bool) and isinstance(saved[key], bool)
                                         or key in {"mode", "scope"} and isinstance(saved[key], str)):
                        result[key] = saved[key]
        except (ValueError, TypeError):
            pass
    if result["mode"] not in VALID_MODES:
        result["mode"] = "preview"
    result["capabilities"] = dict(CAPABILITIES)
    result["owner_approval_required_for_changes"] = True
    result["workspace_scope"] = "configured_workspace"
    return result


def update_policy(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = set(DEFAULT_POLICY)
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError("Unsupported policy fields: " + ", ".join(sorted(unknown)))
    current = get_policy()
    for key, value in payload.items():
        if key in CAPABILITIES and not isinstance(value, bool):
            raise ValueError(f"{key} must be true or false.")
        if key == "mode" and value not in VALID_MODES:
            raise ValueError("mode must be preview, ask_before_changes, or authorised_automation.")
        if key == "scope" and value != "configured_workspace":
            raise ValueError("LazHelper can only operate inside the configured workspace.")
        current[key] = value
    stored = {key: current[key] for key in DEFAULT_POLICY}
    with _connect() as con:
        con.execute(
            "INSERT INTO owner_policy(id,value,updated_at) VALUES(1,?,?) "
            "ON CONFLICT(id) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
            (json.dumps(stored), _now()),
        )
    return get_policy()


def require(capability: str) -> None:
    if capability not in CAPABILITIES:
        raise ValueError("Unknown capability.")
    if not get_policy().get(capability, False):
        raise PermissionError(f"Owner permission is disabled: {CAPABILITIES[capability]}.")


def list_instructions() -> list[dict[str, Any]]:
    with _connect() as con:
        rows = con.execute(
            "SELECT id,scope,scope_path,instruction,enabled,created_at,updated_at "
            "FROM owner_instructions ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def save_instructions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(items) > 50:
        raise ValueError("At most 50 instruction rules may be saved.")
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each instruction rule must be an object.")
        scope = item.get("scope", "global")
        path = item.get("scope_path", "")
        instruction = item.get("instruction", "")
        enabled = item.get("enabled", True)
        if scope not in {"global", "folder", "task"}:
            raise ValueError("Instruction scope must be global, folder, or task.")
        if not isinstance(path, str) or len(path) > 500 or path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
            raise ValueError("Instruction scope path must be workspace-relative.")
        if scope == "global":
            path = ""
        if scope == "folder" and not path.strip():
            raise ValueError("Folder instructions need a workspace-relative folder.")
        if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 2000:
            raise ValueError("Instructions must contain 1–2000 characters.")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false.")
        cleaned.append((scope, path.replace("\\", "/").strip("/"), instruction.strip(), enabled))
    now = _now()
    with _connect() as con:
        con.execute("DELETE FROM owner_instructions")
        con.executemany(
            "INSERT INTO owner_instructions(scope,scope_path,instruction,enabled,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?)",
            [(scope, path, instruction, int(enabled), now, now) for scope, path, instruction, enabled in cleaned],
        )
    return list_instructions()
