"""Stages F–K: recovery visibility, project workspaces, archive inspection,
safe natural-language routing, local evidence retrieval, and read-only workflows.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from . import config, organizer, workspace_intelligence
from .extractor import extract_file
from .scanner import safe_file_path, safe_workspace_path, UnsafePath

DB_PATH = config.PROJECT_ROOT / ".lazhelper_extended.sqlite3"
MAX_ARCHIVE_ENTRIES = 1000
MAX_ARCHIVE_UNCOMPRESSED = 128 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 8 * 1024 * 1024
MAX_WORKFLOWS = 100
WORKFLOW_ACTIONS = {"search", "relationships", "duplicates", "health_report", "knowledge_map"}
PROJECT_TYPES = {"study", "research", "work", "personal", "development", "other"}
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".html", ".css", ".sql", ".sh"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS project_workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        folder_path TEXT NOT NULL DEFAULT '.',
        tags_json TEXT NOT NULL DEFAULT '[]',
        structure_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS saved_workflows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        steps_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    con.commit()
    return con


def _inside_folder(relative_path: str) -> str:
    folder = safe_workspace_path(relative_path)
    return folder.relative_to(config.ALLOWED_ROOT.resolve()).as_posix() or "."


def recovery_history(limit: int = 100, export_format: str = "json") -> dict[str, Any]:
    rows = organizer.list_journal(limit)
    if export_format == "csv":
        output = io.StringIO()
        fields = ["id", "action", "source_path", "destination_path", "status", "created_at", "undone_at", "detail"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return {"format": "csv", "filename": "lazhelper-recovery-history.csv", "content": output.getvalue(),
                "count": len(rows), "message": "History export only; no files were changed."}
    if export_format != "json":
        raise ValueError("format must be json or csv.")
    return {"format": "json", "filename": "lazhelper-recovery-history.json", "operations": rows,
            "count": len(rows), "message": "History export only; no files were changed."}


def inspect_recovery(operation_id: int) -> dict[str, Any]:
    rows = [row for row in organizer.list_journal(200) if row["id"] == operation_id]
    if not rows:
        raise ValueError("Operation was not found in the recent journal.")
    row = rows[0]
    root = config.ALLOWED_ROOT.resolve()
    source_exists = destination_exists = False
    source_error = destination_error = None
    for key, rel in (("source", row.get("source_path")), ("destination", row.get("destination_path"))):
        if not rel:
            continue
        try:
            path = safe_file_path(rel)
            if key == "source":
                source_exists = path.exists()
            else:
                destination_exists = path.exists()
        except FileNotFoundError:
            if key == "source":
                source_error = "File not currently present at this path."
            else:
                destination_error = "File not currently present at this path."
        except (UnsafePath, ValueError) as exc:
            if key == "source":
                source_error = str(exc)
            else:
                destination_error = str(exc)
    can_undo = row["status"] == "applied" and not row.get("undone_at") and destination_exists and not source_exists
    return {"operation": row, "source_exists": source_exists, "destination_exists": destination_exists,
            "source_note": source_error, "destination_note": destination_error, "currently_safe_to_offer_undo": can_undo,
            "message": "This is a current-state check, not a guarantee. Undo revalidates paths and destination conflicts before acting."}


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    kind = str(payload.get("kind", "study")).strip().lower()
    description = str(payload.get("description", "")).strip()
    folder_path = _inside_folder(str(payload.get("folder_path", ".")))
    tags = payload.get("tags", [])
    if not name or len(name) > 100:
        raise ValueError("Project name must contain 1–100 characters.")
    if kind not in PROJECT_TYPES:
        raise ValueError("Choose a supported project type.")
    if len(description) > 1000:
        raise ValueError("Description must be 1000 characters or fewer.")
    if not isinstance(tags, list) or len(tags) > 30:
        raise ValueError("Tags must be a list of at most 30 items.")
    cleaned_tags = sorted({str(tag).strip()[:40] for tag in tags if str(tag).strip()})
    structure = payload.get("structure", [])
    if not isinstance(structure, list) or len(structure) > 30:
        raise ValueError("Structure must contain at most 30 folder names.")
    cleaned_structure = []
    for entry in structure:
        value = str(entry).strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value or any(c in value for c in ':<>|"?*'):
            raise ValueError("Structure entries must be simple folder names.")
        if len(value) > 80:
            raise ValueError("Folder names must be 80 characters or fewer.")
        if value not in cleaned_structure:
            cleaned_structure.append(value)
    now = _now()
    with _connect() as con:
        cur = con.execute("INSERT INTO project_workspaces(name,kind,description,folder_path,tags_json,structure_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                          (name, kind, description, folder_path, json.dumps(cleaned_tags), json.dumps(cleaned_structure), now, now))
        project_id = cur.lastrowid
    return get_project(project_id)


def _project(row) -> dict[str, Any]:
    result = dict(row)
    result["tags"] = json.loads(result.pop("tags_json"))
    result["suggested_structure"] = json.loads(result.pop("structure_json"))
    return result


def list_projects() -> dict[str, Any]:
    with _connect() as con:
        rows = con.execute("SELECT * FROM project_workspaces ORDER BY updated_at DESC LIMIT 500").fetchall()
    return {"projects": [_project(row) for row in rows], "count": len(rows)}


def get_project(project_id: int) -> dict[str, Any]:
    with _connect() as con:
        row = con.execute("SELECT * FROM project_workspaces WHERE id=?", (project_id,)).fetchone()
    if not row:
        raise ValueError("Project workspace not found.")
    return _project(row)


def update_project(project_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    current = get_project(project_id)
    allowed = {"name", "kind", "description", "folder_path", "tags", "structure"}
    if set(payload) - allowed:
        raise ValueError("Unsupported project fields.")
    merged = {
        "name": current["name"], "kind": current["kind"], "description": current["description"],
        "folder_path": current["folder_path"], "tags": current["tags"], "structure": current["suggested_structure"],
    }
    merged.update(payload)
    name = str(merged["name"]).strip()
    kind = str(merged["kind"]).strip().lower()
    if not name or len(name) > 100 or kind not in PROJECT_TYPES:
        raise ValueError("Provide a valid project name and kind.")
    folder_path = _inside_folder(str(merged["folder_path"]))
    tags = merged["tags"]
    structure = merged["structure"]
    if not isinstance(tags, list) or len(tags) > 30 or not isinstance(structure, list) or len(structure) > 30:
        raise ValueError("Tags and structure must be lists of at most 30 entries.")
    cleaned_structure = []
    for entry in structure:
        value = str(entry).strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value or any(c in value for c in ':<>|"?*'):
            raise ValueError("Structure entries must be simple folder names.")
        if value not in cleaned_structure:
            cleaned_structure.append(value[:80])
    with _connect() as con:
        con.execute("UPDATE project_workspaces SET name=?,kind=?,description=?,folder_path=?,tags_json=?,structure_json=?,updated_at=? WHERE id=?",
                    (name, kind, str(merged["description"])[:1000], folder_path,
                     json.dumps(sorted({str(x).strip()[:40] for x in tags if str(x).strip()})),
                     json.dumps(cleaned_structure), _now(), project_id))
    return get_project(project_id)


def delete_project(project_id: int) -> dict[str, Any]:
    with _connect() as con:
        cur = con.execute("DELETE FROM project_workspaces WHERE id=?", (project_id,))
    if cur.rowcount == 0:
        raise ValueError("Project workspace not found.")
    return {"id": project_id, "deleted_metadata_only": True, "message": "Project metadata removed; no workspace files or folders were changed."}


def project_overview(project_id: int) -> dict[str, Any]:
    project = get_project(project_id)
    scan = workspace_intelligence.workspace_health_report(project["folder_path"], 300)
    return {"project": project, "files_count": scan["files_count"], "extension_counts": scan["extension_counts"],
            "health_findings": scan["findings"][:40],
            "message": "Project overview uses the selected folder and metadata only. Suggested folder structure is not created automatically."}


def inspect_archive(relative_path: str, max_entries: int = 500, preview_text: bool = False) -> dict[str, Any]:
    archive_path = safe_file_path(relative_path)
    if archive_path.suffix.lower() != ".zip":
        raise ValueError("Only ZIP archives are supported.")
    if archive_path.stat().st_size > config.MAX_FILE_BYTES:
        raise ValueError("Archive exceeds the configured file-size limit.")
    entries = []
    warnings = []
    total_size = 0
    unsafe_count = 0
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        bounded = infos[:max(1, min(max_entries, MAX_ARCHIVE_ENTRIES))]
        if len(infos) > len(bounded):
            warnings.append("Archive entry limit reached; inventory is incomplete.")
        for info in bounded:
            raw = info.filename.replace("\\", "/")
            name = PurePosixPath(raw)
            mode = (info.external_attr >> 16) & 0o170000
            reasons = []
            if raw.startswith("/") or name.is_absolute() or ".." in name.parts or (name.parts and ":" in name.parts[0]):
                reasons.append("unsafe path")
            if mode == 0o120000:
                reasons.append("symbolic link")
            if info.flag_bits & 0x1:
                reasons.append("encrypted entry")
            if info.file_size < 0 or info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                reasons.append("member size limit")
            if total_size + max(0, info.file_size) > MAX_ARCHIVE_UNCOMPRESSED:
                reasons.append("total expanded-size limit")
            if info.file_size > max(1, info.compress_size) * 200 and info.file_size > 1024 * 1024:
                reasons.append("suspicious compression ratio")
            if reasons:
                unsafe_count += 1
            else:
                total_size += info.file_size
            item = {"name": raw[:240], "size_bytes": info.file_size, "compressed_bytes": info.compress_size,
                    "directory": info.is_dir(), "safe_to_preview": not reasons and Path(raw).suffix.lower() in TEXT_SUFFIXES and info.file_size <= 64 * 1024,
                    "warnings": reasons}
            if preview_text and item["safe_to_preview"] and not info.is_dir():
                try:
                    with archive.open(info, "r") as stream:
                        raw_bytes = stream.read(64 * 1024 + 1)
                    if len(raw_bytes) <= 64 * 1024:
                        item["text_preview"] = raw_bytes.decode("utf-8", errors="replace")[:2000]
                except (OSError, RuntimeError, zipfile.BadZipFile):
                    item["warnings"].append("preview read failed")
            entries.append(item)
    return {"archive": archive_path.relative_to(config.ALLOWED_ROOT.resolve()).as_posix(),
            "entries": entries, "entries_total": len(infos), "entries_inspected": len(entries),
            "safe_entries": sum(not item["warnings"] for item in entries), "flagged_entries": unsafe_count,
            "expanded_bytes_considered": total_size, "limits": {"entries": MAX_ARCHIVE_ENTRIES, "member_bytes": MAX_ARCHIVE_MEMBER_BYTES,
            "total_expanded_bytes": MAX_ARCHIVE_UNCOMPRESSED, "preview_member_bytes": 64 * 1024},
            "truncated": len(infos) > len(entries), "extracted": False,
            "message": "Inventory only. No extraction occurred. Flagged paths, links, encrypted entries, and oversized members are not previewed."}


def preview_command(command: str, relative_path: str = ".") -> dict[str, Any]:
    text = (command or "").strip()
    if not text or len(text) > 500:
        raise ValueError("Enter a command between 1 and 500 characters.")
    root = _inside_folder(relative_path)
    lowered = text.casefold()
    intent = None
    params: dict[str, Any] = {"relative_path": root}
    if any(term in lowered for term in ("duplicate", "same file", "copies")):
        intent = "duplicates"
    elif any(term in lowered for term in ("relationship", "related file", "belong together")):
        intent = "relationships"
    elif any(term in lowered for term in ("health", "messy", "problem", "review my workspace")):
        intent = "health_report"
    elif any(term in lowered for term in ("knowledge map", "map my files", "file map")):
        intent = "knowledge_map"
    elif any(term in lowered for term in ("find ", "search ", "look for ", "where is ", "about ")):
        intent = "search"
        match = re.search(r"(?:find|search(?: for)?|look for|where is|about)\s+(.+)", text, re.I)
        if match:
            params["query"] = match.group(1).strip(" .?!\"'")[:300]
    elif "archive" in lowered or "zip file" in lowered:
        intent = "archive_inspection"
        match = re.search(r"([\w ./-]+\.zip)", text, re.I)
        if match:
            params["archive_path"] = match.group(1).strip()
    elif any(term in lowered for term in ("project", "study workspace", "research workspace")):
        intent = "project_workspace"
    actions = {
        "search": "Search filenames and supported extracted content.",
        "duplicates": "Identify exact duplicates and possible version/similar-content candidates.",
        "relationships": "Find explainable candidate relationships from names and folder context.",
        "health_report": "Create an advisory workspace health checklist.",
        "knowledge_map": "Build a lightweight map of files and candidate relationships.",
        "archive_inspection": "Inspect a ZIP inventory without extracting files.",
        "project_workspace": "Open project workspace tools; no project or folders will be created by this preview.",
    }
    if intent is None:
        return {"command": text, "understood": False, "intent": None, "parameters": params,
                "message": "I couldn't safely map that request to a supported action. Try asking to search, find duplicates, show related files, check workspace health, build a knowledge map, inspect a ZIP archive, or manage a project workspace."}
    return {"command": text, "understood": True, "intent": intent, "parameters": params,
            "proposed_action": actions[intent], "requires_confirmation": True,
            "message": "This is a preview only. The command parser does not move, rename, overwrite, extract, or delete files."}


def ask_local_knowledge(question: str, relative_path: str = ".", max_sources: int = 5) -> dict[str, Any]:
    question = (question or "").strip()
    if not question or len(question) > 500:
        raise ValueError("Enter a question between 1 and 500 characters.")
    root = _inside_folder(relative_path)
    from .scanner import scan_folder
    scan = scan_folder(root)
    qtokens = {x.casefold() for x in re.findall(r"[a-z0-9]{2,}", question)
               if x.casefold() not in {"what", "where", "when", "which", "does", "have", "with", "from", "that", "this", "your", "about", "tell", "show", "find", "are", "the", "for"}}
    candidates = []
    considered = 0
    for item in scan["files"][:300]:
        if not item.readable or item.size_bytes > config.MAX_FILE_BYTES:
            continue
        considered += 1
        try:
            extracted = extract_file(item.relative_path)
            content = str(extracted.get("text") or "")
        except Exception:
            continue
        sentences = re.split(r"(?<=[.!?])\s+|\n+", content)
        ranked = []
        for sentence in sentences:
            sentence = " ".join(sentence.split()).strip()
            if len(sentence) < 20:
                continue
            words = {x.casefold() for x in re.findall(r"[a-z0-9]{2,}", sentence)}
            overlap = len(qtokens & words) / max(1, len(qtokens))
            if overlap >= 0.2:
                ranked.append((overlap, sentence[:450]))
        # If sentence token overlap is too sparse, retain a short local excerpt only
        # when at least one meaningful query token is literally present in the content.
        if not ranked and qtokens and content:
            folded = content.casefold()
            matching = [token for token in qtokens if token in folded]
            if matching:
                ranked.append((min(0.25, len(matching) / max(1, len(qtokens))), " ".join(content.split())[:450]))
        for score, sentence in sorted(ranked, key=lambda row: (-row[0], row[1]))[:2]:
            candidates.append({"path": item.relative_path, "score": round(score, 3), "evidence": sentence})
    candidates.sort(key=lambda row: (-row["score"], row["path"]))
    unique = []
    seen = set()
    for row in candidates:
        key = (row["path"], row["evidence"])
        if key not in seen:
            unique.append(row)
            seen.add(key)
    sources = unique[:max(1, min(max_sources, 10))]
    if sources:
        answer = "Based on your local documents, the most relevant evidence is: " + " ".join(
            f'“{source["evidence"]}” (source: {source["path"]}).' for source in sources[:3]
        ) + " This is extractive evidence, not a guarantee that the documents contain the complete answer."
    else:
        answer = "I couldn't find a sufficiently relevant passage in the selected workspace. Try different keywords or choose another folder."
    return {"question": question, "answer": answer, "sources": sources, "source_count": len(sources),
            "files_considered": considered, "truncated": scan["truncated"] or len(scan["files"]) > 300,
            "message": "Local retrieval only. Document content is not sent to an AI service; results are grounded in quoted source passages."}


def create_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    steps = payload.get("steps")
    if not name or len(name) > 100:
        raise ValueError("Workflow name must contain 1–100 characters.")
    if len(description) > 500:
        raise ValueError("Workflow description must be 500 characters or fewer.")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 10:
        raise ValueError("A workflow must contain between 1 and 10 steps.")
    cleaned = []
    for step in steps:
        if not isinstance(step, dict) or step.get("action") not in WORKFLOW_ACTIONS:
            raise ValueError("Workflow steps may only use supported read-only actions.")
        params = step.get("parameters", {})
        if not isinstance(params, dict):
            raise ValueError("Each step's parameters must be an object.")
        if set(params) - {"query", "relative_path"}:
            raise ValueError("Unsupported workflow parameter.")
        root = _inside_folder(str(params.get("relative_path", ".")))
        item = {"action": step["action"], "parameters": {"relative_path": root}}
        if step["action"] == "search":
            query = str(params.get("query", "")).strip()
            if not query or len(query) > 300:
                raise ValueError("Search workflow steps require a query of 1–300 characters.")
            item["parameters"]["query"] = query
        cleaned.append(item)
    with _connect() as con:
        count = con.execute("SELECT COUNT(*) FROM saved_workflows").fetchone()[0]
        if count >= MAX_WORKFLOWS:
            raise ValueError("Workflow limit reached.")
        now = _now()
        cur = con.execute("INSERT INTO saved_workflows(name,description,steps_json,created_at,updated_at) VALUES(?,?,?,?,?)",
                          (name, description, json.dumps(cleaned), now, now))
        workflow_id = cur.lastrowid
    return get_workflow(workflow_id)


def _workflow(row) -> dict[str, Any]:
    result = dict(row)
    result["steps"] = json.loads(result.pop("steps_json"))
    return result


def list_workflows() -> dict[str, Any]:
    with _connect() as con:
        rows = con.execute("SELECT * FROM saved_workflows ORDER BY updated_at DESC LIMIT ?", (MAX_WORKFLOWS,)).fetchall()
    return {"workflows": [_workflow(row) for row in rows], "count": len(rows)}


def get_workflow(workflow_id: int) -> dict[str, Any]:
    with _connect() as con:
        row = con.execute("SELECT * FROM saved_workflows WHERE id=?", (workflow_id,)).fetchone()
    if not row:
        raise ValueError("Workflow not found.")
    return _workflow(row)


def delete_workflow(workflow_id: int) -> dict[str, Any]:
    with _connect() as con:
        cur = con.execute("DELETE FROM saved_workflows WHERE id=?", (workflow_id,))
    if not cur.rowcount:
        raise ValueError("Workflow not found.")
    return {"id": workflow_id, "message": "Saved workflow removed. No workspace files were changed."}


def run_workflow(workflow_id: int) -> dict[str, Any]:
    workflow = get_workflow(workflow_id)
    results = []
    for index, step in enumerate(workflow["steps"], start=1):
        action = step["action"]
        params = step["parameters"]
        if action == "search":
            result = workspace_intelligence.content_search(params["query"], params["relative_path"])
        elif action == "relationships":
            result = workspace_intelligence.file_relationships(params["relative_path"])
        elif action == "duplicates":
            result = workspace_intelligence.duplicate_insights(params["relative_path"])
        elif action == "health_report":
            result = workspace_intelligence.workspace_health_report(params["relative_path"])
        elif action == "knowledge_map":
            result = workspace_intelligence.knowledge_map(params["relative_path"])
        else:
            raise ValueError("Unsupported workflow action.")
        results.append({"step": index, "action": action, "result": result})
    return {"workflow": workflow, "results": results, "files_changed": False,
            "message": "Workflow completed as read-only analysis. No move, rename, extraction, overwrite, or deletion was performed."}
