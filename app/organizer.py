"""Review-first organisation, duplicate detection, uncertainty queue, journal and preferences.

All operations are confined to the configured workspace. Moves only happen after an
explicit apply request; destination collisions are never overwritten.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from . import config, database
from .scanner import (
    safe_file_path,
    open_workspace_file,
    create_workspace_file,
    ensure_workspace_directory,
    unlink_workspace_file,
    UnsafePath,
)

DB_PATH = config.PROJECT_ROOT / ".lazydesk_state.sqlite3"

DEFAULT_PREFERENCES = {
    "category_rules": {
        "Documents": [".pdf", ".docx", ".txt", ".md", ".rtf"],
        "Spreadsheets": [".csv", ".xls", ".xlsx"],
        "Presentations": [".pptx"],
        "Images": [".png", ".jpg", ".jpeg", ".webp"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".h", ".cpp", ".go", ".rs", ".sh", ".sql"],
        "Archives": [".zip"],
    },
    "keep_originals": False,
    "review_all_moves": True,
    "include_date_in_plan": False,
}
def _connect():
    return database.connect(DB_PATH)
def _now():
    return datetime.now(timezone.utc).isoformat()

def _move_no_overwrite(source: Path, destination: Path):
    """Move one regular file using no-follow handles and exclusive creation."""
    root = config.ALLOWED_ROOT.resolve()
    source_rel = source.relative_to(root).as_posix()
    destination_rel = destination.relative_to(root).as_posix()
    source_stat = None
    created_stat = None

    try:
        with open_workspace_file(source_rel) as src:
            source_stat = os.fstat(src.fileno())
            ensure_workspace_directory(Path(destination_rel).parent)

            with create_workspace_file(destination_rel) as dst:
                created_stat = os.fstat(dst.fileno())
                shutil.copyfileobj(src, dst, length=1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
                if hasattr(os, "fchmod"):
                    os.fchmod(dst.fileno(), source_stat.st_mode & 0o777)
                if os.name == "posix":
                    os.utime(
                        dst.fileno(),
                        ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns)
                    )
                created_stat = os.fstat(dst.fileno())

            unlink_workspace_file(source_rel, source_stat)

    except Exception:
        if created_stat is not None:
            try:
                unlink_workspace_file(destination_rel, created_stat)
            except (OSError, ValueError):
                pass
        raise

def get_preferences():
    with _connect() as con:
        rows = {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT key,value FROM preferences")}
    result = json.loads(json.dumps(DEFAULT_PREFERENCES))
    result.update(rows)
    return result
def save_preferences(payload: dict[str, Any]):
    allowed = {"category_rules", "keep_originals", "review_all_moves", "include_date_in_plan"}
    if set(payload) - allowed:
        raise ValueError("Only supported preference fields can be changed.")
    current = get_preferences()
    current.update(payload)
    rules = current.get("category_rules")
    if not isinstance(rules, dict) or len(rules) > 20:
        raise ValueError("Category rules must be an object with at most 20 categories.")
    cleaned = {}
    for category, extensions in rules.items():
        name = str(category).strip()
        if not name or name in {".", ".."} or any(c in name for c in '/\\:<>|"?*') or len(name) > 40:
            raise ValueError("Category names must be simple folder names.")
        if not isinstance(extensions, list) or len(extensions) > 80:
            raise ValueError("Each category must contain a list of extensions.")
        cleaned[name] = sorted({str(ext).lower() if str(ext).startswith(".") else "."+str(ext).lower() for ext in extensions})
    current["category_rules"] = cleaned
    for key in ("keep_originals", "review_all_moves", "include_date_in_plan"):
        if not isinstance(current[key], bool):
            raise ValueError(f"{key} must be true or false.")
    with _connect() as con:
        for key, value in current.items():
            con.execute("INSERT INTO preferences(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                        (key, json.dumps(value), _now()))
    return current
def _category_for(path: Path, rules: dict[str, list[str]]) -> str | None:
    ext = path.suffix.lower()
    for category, extensions in rules.items():
        if ext in extensions:
            return category
    return None
def build_plan(relative_paths: list[str]):
    if not relative_paths or len(relative_paths) > 500:
        raise ValueError("Choose between 1 and 500 files for a plan.")
    prefs = get_preferences()
    rules = prefs["category_rules"]
    plan = []
    seen = set()
    for raw in relative_paths:
        path = safe_file_path(raw)
        rel = path.relative_to(config.ALLOWED_ROOT.resolve()).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        category = _category_for(path, rules)
        if not category:
            queue_item(rel, "No matching category rule; manual review needed.")
            plan.append({"source": rel, "destination": None, "status": "needs_review", "reason": "No matching category rule"})
            continue
        destination = f"{category}/{path.name}"
        if prefs.get("include_date_in_plan"):
            stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m")
            destination = f"{category}/{stamp}/{path.name}"
        # Plans never overwrite; collisions are flagged before apply.
        target = (config.ALLOWED_ROOT.resolve() / destination).resolve()
        try: target.relative_to(config.ALLOWED_ROOT.resolve())
        except ValueError: raise UnsafePath("Proposed destination escaped workspace.")
        if target.exists():
            plan.append({"source": rel, "destination": destination, "status": "conflict", "reason": "Destination already exists; nothing will be overwritten"})
        elif rel == destination:
            plan.append({"source": rel, "destination": destination, "status": "already_organised", "reason": "Already in the proposed location"})
        else:
            plan.append({"source": rel, "destination": destination, "status": "ready", "reason": "Rule matched file extension"})
    return {"plan": plan, "ready_count": sum(x["status"] == "ready" for x in plan),
            "review_count": sum(x["status"] == "needs_review" for x in plan),
            "conflict_count": sum(x["status"] == "conflict" for x in plan),
            "message": "Preview only. No files were changed."}
def apply_plan(items: list[dict[str, str]]):
    if not items or len(items) > 500:
        raise ValueError("Choose between 1 and 500 reviewed plan items.")

    completed, failed, pending_recovery = [], [], []
    files_changed = 0
    root = config.ALLOWED_ROOT.resolve()

    for item in items:
        source_rel = item.get("source", "")
        dest_rel = item.get("destination", "")
        journal_id = None
        moved = False

        if not source_rel or not dest_rel or item.get("approved") is not True:
            failed.append({
                "source": source_rel,
                "reason": "Each move must be explicitly approved."
            })
            continue

        try:
            source = safe_file_path(source_rel)
            dest_part = Path(dest_rel)
            if dest_part.is_absolute() or ".." in dest_part.parts or "\\" in dest_rel:
                raise UnsafePath("Destination must be a safe relative workspace path.")

            cursor = root
            for part in dest_part.parts:
                if part in ("", ".") or any(c in part for c in '\\:<>|"?*'):
                    raise UnsafePath("Invalid destination path.")
                cursor = cursor / part
                if cursor.is_symlink():
                    raise UnsafePath("Destination traverses a symlink.")

            destination = (root / dest_part).resolve()
            destination.relative_to(root)
            if destination.exists():
                raise FileExistsError("Destination already exists; refusing to overwrite.")
            if source == destination:
                raise ValueError("Source and destination are identical.")

            normalized_destination = destination.relative_to(root).as_posix()

            # Persist intent before changing the filesystem. A crash during the move
            # leaves a visible pending journal row instead of an untracked move.
            with _connect() as con:
                cur = con.execute(
                    "INSERT INTO operation_journal "
                    "(action,source_path,destination_path,status,created_at,detail) "
                    "VALUES(?,?,?,?,?,?) RETURNING id",
                    (
                        "move",
                        source_rel,
                        normalized_destination,
                        "pending",
                        _now(),
                        "User-approved move; operation started."
                    )
                )
                journal_id = cur.fetchone()["id"]

            ensure_workspace_directory(dest_part.parent)
            if not source.exists() or destination.exists():
                raise FileExistsError(
                    "Source changed or destination appeared during review."
                )

            _move_no_overwrite(source, destination)
            moved = True
            files_changed += 1

            with _connect() as con:
                con.execute(
                    "UPDATE operation_journal SET status='applied', detail=? WHERE id=?",
                    ("User-approved move completed.", journal_id)
                )

            completed.append({
                "id": journal_id,
                "source": source_rel,
                "destination": normalized_destination
            })

        except Exception as exc:
            if journal_id is not None and not moved:
                try:
                    with _connect() as con:
                        con.execute(
                            "UPDATE operation_journal SET status='failed', detail=? WHERE id=?",
                            (str(exc)[:500], journal_id)
                        )
                except Exception:
                    pass
            if journal_id is not None and moved:
                pending_recovery.append({
                    "id": journal_id,
                    "source": source_rel,
                    "destination": dest_rel,
                    "reason": (
                        "The file move completed, but the journal could not be finalized. "
                        "The operation remains marked pending for recovery."
                    )
                })
            else:
                failed.append({"source": source_rel, "reason": str(exc)})

    return {
        "completed": completed,
        "failed": failed,
        "pending_recovery": pending_recovery,
        "files_changed": files_changed
    }


def undo_operation(operation_id: int):
    root = config.ALLOWED_ROOT.resolve()

    with _connect() as con:
        row = con.execute(
            "SELECT * FROM operation_journal WHERE id=?",
            (operation_id,)
        ).fetchone()
        if not row:
            raise ValueError("Operation was not found.")
        if row["status"] != "applied" or row["undone_at"]:
            raise ValueError("This operation is not available to undo.")

        source_rel = row["source_path"]
        dest_rel = row["destination_path"]
        dest = safe_file_path(dest_rel)
        source_part = Path(source_rel)
        if (
            source_part.is_absolute()
            or ".." in source_part.parts
            or "\\" in source_rel
        ):
            raise UnsafePath("Journal source path is invalid.")
        source = root / source_part
        source.resolve().relative_to(root)
        if source.exists() or source.is_symlink():
            raise FileExistsError("Original path now exists; undo will not overwrite it.")

        # Record the intent and release the DB connection before moving the file.
        con.execute(
            "UPDATE operation_journal SET status='undoing', detail=? WHERE id=?",
            ("Undo started.", operation_id)
        )

    try:
        ensure_workspace_directory(source_part.parent)
        _move_no_overwrite(dest, source)
    except Exception:
        with _connect() as con:
            con.execute(
                "UPDATE operation_journal SET status='applied', detail=? WHERE id=?",
                ("Undo failed; original move remains applied.", operation_id)
            )
        raise

    with _connect() as con:
        con.execute(
            "UPDATE operation_journal SET status='undone', undone_at=?, detail=? WHERE id=?",
            (_now(), "Move successfully undone.", operation_id)
        )

    return {
        "id": operation_id,
        "restored_path": source_rel,
        "files_changed": 1
    }


def list_journal(limit: int = 100):
    with _connect() as con:
        rows = con.execute("SELECT id,action,source_path,destination_path,status,created_at,undone_at,detail FROM operation_journal ORDER BY id DESC LIMIT ?", (max(1,min(limit,200)),)).fetchall()
    return [dict(r) for r in rows]
def queue_item(path: str, reason: str):
    with _connect() as con:
        con.execute("INSERT INTO review_queue(path,reason,added_at,status) VALUES(?,?,?,'open') ON CONFLICT(path) DO UPDATE SET reason=excluded.reason,status='open'",
                    (path, reason[:500], _now()))
def list_queue():
    with _connect() as con:
        return [dict(r) for r in con.execute("SELECT path,reason,added_at,status FROM review_queue WHERE status='open' ORDER BY added_at DESC LIMIT 500")]
def resolve_queue_item(path: str, decision: str):
    if decision not in {"reviewed", "dismissed"}: raise ValueError("Decision must be reviewed or dismissed.")
    with _connect() as con:
        cur = con.execute("UPDATE review_queue SET status=? WHERE path=? AND status='open'", (decision, path))
        if cur.rowcount == 0: raise ValueError("Open review item not found.")
    return {"path": path, "status": decision}
def find_duplicates(relative_path: str = "."):
    from .scanner import scan_folder

    result = scan_folder(relative_path)
    groups: dict[str, list[dict[str, Any]]] = {}
    checked = 0

    for record in result["files"]:
        if record.size_bytes > config.MAX_FILE_BYTES:
            continue
        digest = hashlib.sha256()
        try:
            with open_workspace_file(record.relative_path) as stream:
                file_stat = os.fstat(stream.fileno())
                if file_stat.st_size > config.MAX_FILE_BYTES:
                    continue
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            groups.setdefault(digest.hexdigest(), []).append({
                "path": record.relative_path,
                "size_bytes": file_stat.st_size,
            })
            checked += 1
        except (OSError, ValueError):
            continue

    duplicates = [
        {"sha256": digest, "files": files, "count": len(files)}
        for digest, files in groups.items()
        if len(files) > 1
    ]
    return {
        "groups": duplicates,
        "duplicate_files": sum(group["count"] for group in duplicates),
        "files_checked": checked,
        "truncated": result["truncated"],
        "message": "Exact byte-for-byte matches only. No files were removed or changed.",
    }
