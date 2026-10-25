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
from .scanner import safe_file_path, UnsafePath

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
DB_SCHEMA = "lazhelper"

def _connect():
    con = database.connect(schema=DB_SCHEMA, timeout=10)
    con.execute("""CREATE TABLE IF NOT EXISTS operation_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
        source_path TEXT NOT NULL, destination_path TEXT, status TEXT NOT NULL,
        created_at TEXT NOT NULL, undone_at TEXT, detail TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS preferences (
        key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS review_queue (
        path TEXT PRIMARY KEY, reason TEXT NOT NULL, added_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
    )""")
    con.commit()
    return con
def _now():
    return datetime.now(timezone.utc).isoformat()

def _move_no_overwrite(source: Path, destination: Path):
    """Copy into an exclusively-created destination, then unlink source.

    Unlike os.replace(), opening with mode 'xb' never overwrites a path that
    appeared after the preview. If copying fails, remove the partial destination.
    """
    created = False
    try:
        with source.open("rb") as src, destination.open("xb") as dst:
            created = True
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        try:
            shutil.copystat(source, destination, follow_symlinks=False)
        except OSError:
            pass
        source.unlink()
    except Exception:
        if created and source.exists():
            try:
                destination.unlink(missing_ok=True)
            except OSError:
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
    completed, failed = [], []
    root = config.ALLOWED_ROOT.resolve()
    for item in items:
        source_rel, dest_rel = item.get("source", ""), item.get("destination", "")
        if not source_rel or not dest_rel or item.get("approved") is not True:
            failed.append({"source": source_rel, "reason": "Each move must be explicitly approved."}); continue
        try:
            source = safe_file_path(source_rel)
            dest_part = Path(dest_rel)
            if dest_part.is_absolute() or ".." in dest_part.parts:
                raise UnsafePath("Destination must be relative to workspace.")
            # Restrict destination to clean path segments; no symlink traversal.
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
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Re-check source after directory creation and never overwrite a target.
            if not source.exists() or destination.exists():
                raise FileExistsError("Source changed or destination appeared during review.")
            _move_no_overwrite(source, destination)
            with _connect() as con:
                cur = con.execute("INSERT INTO operation_journal(action,source_path,destination_path,status,created_at,detail) VALUES(?,?,?,?,?,?)",
                                  ("move", source_rel, destination.relative_to(root).as_posix(), "applied", _now(), "User-approved move"))
                journal_id = cur.lastrowid
            completed.append({"id": journal_id, "source": source_rel, "destination": destination.relative_to(root).as_posix()})
        except Exception as exc:
            failed.append({"source": source_rel, "reason": str(exc)})
    return {"completed": completed, "failed": failed, "files_changed": len(completed)}
def undo_operation(operation_id: int):
    root = config.ALLOWED_ROOT.resolve()
    with _connect() as con:
        row = con.execute("SELECT * FROM operation_journal WHERE id=?", (operation_id,)).fetchone()
        if not row: raise ValueError("Operation was not found.")
        if row["status"] != "applied" or row["undone_at"]:
            raise ValueError("This operation is not available to undo.")
        source_rel, dest_rel = row["source_path"], row["destination_path"]
        dest = safe_file_path(dest_rel)
        source_part = Path(source_rel)
        if source_part.is_absolute() or ".." in source_part.parts:
            raise UnsafePath("Journal source path is invalid.")
        source = (root / source_part).resolve()
        source.relative_to(root)
        if source.exists():
            raise FileExistsError("Original path now exists; undo will not overwrite it.")
        source.parent.mkdir(parents=True, exist_ok=True)
        _move_no_overwrite(dest, source)
        con.execute("UPDATE operation_journal SET status='undone',undone_at=? WHERE id=?", (_now(), operation_id))
    return {"id": operation_id, "restored_path": source_rel, "files_changed": 1}
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
    from .scanner import safe_workspace_path
    folder = safe_workspace_path(relative_path)
    groups: dict[str, list[dict[str, Any]]] = {}
    checked = 0
    for current, dirs, names in os.walk(folder, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
        for name in names:
            path = Path(current) / name
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size > config.MAX_FILE_BYTES: continue
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                rel = path.relative_to(config.ALLOWED_ROOT.resolve()).as_posix()
                groups.setdefault(digest.hexdigest(), []).append({"path": rel, "size_bytes": path.stat().st_size})
                checked += 1
                if checked >= config.MAX_FILES: break
            except OSError:
                continue
        if checked >= config.MAX_FILES: break
    duplicates = [{"sha256": digest, "files": files, "count": len(files)} for digest, files in groups.items() if len(files) > 1]
    return {"groups": duplicates, "duplicate_files": sum(g["count"] for g in duplicates), "files_checked": checked,
            "message": "Exact byte-for-byte matches only. No files were removed or changed."}
