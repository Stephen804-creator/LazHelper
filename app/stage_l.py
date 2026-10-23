"""Stage L: portable organisation-plan export/import with freshness checks.

Import is deliberately preview-only. It never calls organizer.apply_plan and never
changes workspace files. Applying any accepted move remains a separate, explicit,
per-item approval through the existing organize/apply endpoint.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import config, organizer
from .scanner import safe_file_path, UnsafePath

router = APIRouter(tags=["portable organisation plans"])
PLAN_FORMAT_VERSION = 1
MAX_PLAN_ITEMS = 500
MAX_IMPORT_CHARS = 2_000_000
HASH_LIMIT_BYTES = 32 * 1024 * 1024


class PlanExportRequest(BaseModel):
    relative_paths: list[str] = Field(min_length=1, max_length=MAX_PLAN_ITEMS)
    export_format: str = Field(default="json", pattern="^(json|csv)$")


class PlanImportRequest(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_IMPORT_CHARS)
    import_format: str = Field(default="json", pattern="^(json|csv)$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_file(raw: str) -> tuple[Path, str]:
    path = safe_file_path(raw)
    if not path.is_file():
        raise ValueError(f"Source must be an existing regular file: {raw}")
    rel = path.relative_to(config.ALLOWED_ROOT.resolve()).as_posix()
    return path, rel


def _metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    digest = None
    if stat.st_size <= HASH_LIMIT_BYTES:
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
    return {
        "size_bytes": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": digest,
    }


def _safe_destination(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 1000:
        raise ValueError("Each destination must be a non-empty relative path.")
    value = raw.strip().replace("\\", "/")
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or not candidate.parts or any(
        part in {"", ".", ".."} or ":" in part or any(c in part for c in '<>:"|?*')
        for part in candidate.parts
    ):
        raise ValueError(f"Unsafe destination path: {raw}")
    root = config.ALLOWED_ROOT.resolve()
    cursor = root
    for part in candidate.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"Destination traverses a symbolic link: {raw}")
    try:
        (root / Path(*candidate.parts)).resolve().relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Destination escapes the configured workspace: {raw}") from exc
    return candidate.as_posix()


def _confidence(status: str, has_metadata: bool) -> float:
    if status == "ready":
        return 0.9 if has_metadata else 0.75
    if status == "already_organised":
        return 0.98
    if status == "conflict":
        return 0.1
    return 0.25


def export_plan(relative_paths: list[str], export_format: str = "json") -> dict[str, Any]:
    if export_format not in {"json", "csv"}:
        raise ValueError("Export format must be json or csv.")
    if not relative_paths or len(relative_paths) > MAX_PLAN_ITEMS:
        raise ValueError(f"Choose between 1 and {MAX_PLAN_ITEMS} files.")
    plan_result = organizer.build_plan(relative_paths)
    rows = []
    for item in plan_result["plan"]:
        row = dict(item)
        source = row.get("source")
        metadata = None
        if source:
            path, normalised = _relative_file(source)
            row["source"] = normalised
            metadata = _metadata(path)
        destination = row.get("destination")
        if destination is not None:
            row["destination"] = _safe_destination(destination)
        row["confidence"] = _confidence(str(row.get("status", "")), metadata is not None)
        row["file_metadata"] = metadata
        rows.append(row)
    payload = {
        "schema": "lazhelper.organisation-plan",
        "format_version": PLAN_FORMAT_VERSION,
        "generated_at": _now(),
        "workspace_label": "configured-workspace",
        "items": rows,
        "summary": {
            "total": len(rows),
            "ready": sum(row["status"] == "ready" for row in rows),
            "needs_review": sum(row["status"] == "needs_review" for row in rows),
            "conflicts": sum(row["status"] == "conflict" for row in rows),
            "already_organised": sum(row["status"] == "already_organised" for row in rows),
        },
        "apply_policy": "Preview only. Imported plans must be revalidated and each move explicitly approved.",
    }
    if export_format == "json":
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        mime = "application/json"
        filename = "lazhelper-organisation-plan.json"
    else:
        stream = io.StringIO(newline="")
        fields = ["source", "destination", "status", "reason", "confidence", "file_metadata"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            serialised = dict(row)
            serialised["file_metadata"] = json.dumps(row.get("file_metadata"), separators=(",", ":"))
            writer.writerow(serialised)
        content = stream.getvalue()
        mime = "text/csv"
        filename = "lazhelper-organisation-plan.csv"
    return {"format": export_format, "filename": filename, "content_type": mime,
            "content": content, "item_count": len(rows), "summary": payload["summary"],
            "files_changed": False, "plan": payload if export_format == "json" else None}


def _parse_import(content: str, import_format: str) -> dict[str, Any]:
    if len(content) > MAX_IMPORT_CHARS:
        raise ValueError("Plan content exceeds the 2 MB import limit.")
    if import_format == "json":
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON plan: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON plan must be an object.")
        if payload.get("schema") != "lazhelper.organisation-plan":
            raise ValueError("Unrecognised plan schema.")
        if payload.get("format_version") != PLAN_FORMAT_VERSION:
            raise ValueError("Unsupported organisation-plan format version.")
        items = payload.get("items")
    elif import_format == "csv":
        try:
            items = list(csv.DictReader(io.StringIO(content)))
        except csv.Error as exc:
            raise ValueError("Invalid CSV plan.") from exc
    else:
        raise ValueError("Import format must be json or csv.")
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_PLAN_ITEMS:
        raise ValueError(f"Plan must contain between 1 and {MAX_PLAN_ITEMS} items.")
    return {"items": items}


def import_plan(content: str, import_format: str = "json") -> dict[str, Any]:
    parsed = _parse_import(content, import_format)
    validated = []
    errors = []
    for index, item in enumerate(parsed["items"], start=1):
        if not isinstance(item, dict):
            errors.append({"item": index, "reason": "Plan item must be an object."})
            continue
        source_raw = item.get("source")
        destination_raw = item.get("destination")
        if not isinstance(source_raw, str) or not source_raw.strip():
            errors.append({"item": index, "reason": "Missing source path."})
            continue
        try:
            source_path, source_rel = _relative_file(source_raw)
            destination = _safe_destination(destination_raw)
        except (ValueError, UnsafePath, FileNotFoundError, OSError) as exc:
            errors.append({"item": index, "source": source_raw, "reason": str(exc)})
            continue

        expected = item.get("file_metadata")
        actual = _metadata(source_path)
        if import_format == "csv" and isinstance(expected, str):
            try:
                expected = json.loads(expected) if expected.strip() else None
            except json.JSONDecodeError:
                expected = None
        if expected is not None and not isinstance(expected, dict):
            errors.append({"item": index, "source": source_rel, "reason": "Invalid file_metadata."})
            continue
        changed = False
        if isinstance(expected, dict):
            for key in ("size_bytes", "modified_ns", "sha256"):
                if key in expected and expected.get(key) != actual.get(key):
                    changed = True
        target = (config.ALLOWED_ROOT.resolve() / Path(*PurePosixPath(destination).parts)).resolve()
        collision = target.exists()
        same_path = source_rel == destination
        status = "stale" if changed else ("conflict" if collision else ("already_organised" if same_path else "ready"))
        validated.append({
            "source": source_rel,
            "destination": destination,
            "status": status,
            "original_status": str(item.get("status", "imported")),
            "reason": ("Source file changed since export; review and regenerate the plan." if changed else
                       "Destination currently exists; it will not be overwritten." if collision else
                       "Source and destination are identical." if same_path else
                       "Paths validated against the current workspace; review before approval."),
            "confidence": round(min(max(float(item.get("confidence", 0.5)), 0.0), 1.0), 3)
                          if _is_number(item.get("confidence")) else 0.5,
            "expected_metadata": expected,
            "current_metadata": actual,
            "source_changed": changed,
            "destination_exists": collision,
            "approved": False,
            "requires_explicit_approval": True,
        })
    return {
        "schema": "lazhelper.organisation-plan-import-preview",
        "format_version": PLAN_FORMAT_VERSION,
        "items": validated,
        "errors": errors,
        "valid_count": len(validated),
        "error_count": len(errors),
        "ready_count": sum(item["status"] == "ready" for item in validated),
        "stale_count": sum(item["status"] == "stale" for item in validated),
        "conflict_count": sum(item["status"] == "conflict" for item in validated),
        "files_changed": False,
        "apply_allowed": False,
        "message": "Import is preview-only. Review current paths and metadata; no files were changed. Apply any approved move separately through the existing per-item approval flow.",
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@router.post("/api/plans/export")
async def export_organisation_plan(req: PlanExportRequest):
    try:
        return export_plan(req.relative_paths, req.export_format)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/plans/import")
async def import_organisation_plan(req: PlanImportRequest):
    try:
        return import_plan(req.content, req.import_format)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
