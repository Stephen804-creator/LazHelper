"""Loopback-only Laz Helper local connector API."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import shutil
import tempfile
import time
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__
from .security import (
    APPROVAL_MODES, CAPABILITIES, SCOPE_MODES, PermissionDenied, UnsafePath,
    ensure_no_symlink_components, grant_matches, is_protected, require_grant, validate_existing_path, validate_target_path,
)
from .store import StateStore, new_pairing_code

APP_NAME = "Laz Connector"
DEFAULT_PORT = 43179
DEFAULT_ORIGINS = {
    "https://laz-helper.onrender.com",
    "https://lazhelper.onrender.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}
store = StateStore()
_pair_attempts: dict[str, tuple[int, float]] = {}


def allowed_origins() -> set[str]:
    raw = os.environ.get("LAZ_CONNECTOR_ALLOWED_ORIGINS", "")
    if not raw.strip():
        return set(DEFAULT_ORIGINS)
    return {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}


def _origin(request: Request) -> str:
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or origin not in allowed_origins():
        raise HTTPException(403, "This Laz Helper website origin is not allowed. Review LAZ_CONNECTOR_ALLOWED_ORIGINS.")
    return origin


def _auth(request: Request, authorization: str | None = Header(default=None)) -> str:
    origin = _origin(request)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Connect this browser to Laz Connector first.")
    token = authorization.split(" ", 1)[1].strip()
    saved = store.snapshot().get("paired_origins", {}).get(origin)
    if not saved or not hmac.compare_digest(saved, token):
        raise HTTPException(401, "The device pairing is no longer valid. Connect again.")
    return origin


def _state():
    return store.snapshot()


def _public_grant(grant: dict) -> dict:
    return {
        "id": grant.get("id"), "label": grant.get("label"), "kind": grant.get("kind"),
        "path": grant.get("path"), "capabilities": grant.get("capabilities", []),
        "created_at": grant.get("created_at"),
    }


def _record(action: str, status: str, detail: str):
    store.add_activity(action, status, detail)


def _raise_path_error(exc: Exception):
    if isinstance(exc, PermissionDenied):
        raise HTTPException(403, str(exc)) from exc
    if isinstance(exc, UnsafePath):
        raise HTTPException(400, str(exc)) from exc
    raise HTTPException(400, "The requested path or operation is not allowed.") from exc


def _grant_for(path: Path, capability: str, state: dict) -> None:
    require_grant(state.get("grants", []), path, capability, state.get("scope_mode", "selected_folders"))


def _needs_approval(action: str, state: dict) -> bool:
    if action in {"move", "rename", "delete"}:
        return True
    return state.get("scope_mode") == "ask_every_time" or state.get("approval_mode", "ask_every_time") == "ask_every_time"


def _move_without_overwrite(source: Path, destination: Path) -> None:
    """Copy to an exclusively-created destination, then remove the source."""
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


def _apply_operation(req: "OperationRequest", state: dict) -> dict:
    path = validate_existing_path(req.path) if req.action in {"edit", "move", "rename", "delete"} else validate_target_path(req.path)
    if req.action == "create":
        _grant_for(path.parent, "create", state)
        if path.exists():
            raise HTTPException(409, "A file already exists at that destination; nothing was overwritten.")
        if req.content is None:
            raise HTTPException(422, "Provide text content for a new file.")
        try:
            with path.open("x", encoding="utf-8", newline="") as stream:
                stream.write(req.content)
        except FileExistsError as exc:
            raise HTTPException(409, "A file already exists at that destination; nothing was overwritten.") from exc
        return {"action": "create", "path": str(path), "status": "completed"}

    if req.action == "edit":
        _grant_for(path, "edit", state)
        if not path.is_file():
            raise HTTPException(400, "Only individual files can be edited.")
        if req.content is None:
            raise HTTPException(422, "Provide replacement text for the file.")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, delete=False) as temp:
            temp.write(req.content)
            temp_path = Path(temp.name)
        try:
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)
        return {"action": "edit", "path": str(path), "status": "completed"}

    if req.action in {"move", "rename"}:
        capability = "move" if req.action == "move" else "rename"
        _grant_for(path, capability, state)
        if not path.is_file():
            raise HTTPException(400, "Only individual files can be moved or renamed.")
        if not req.destination:
            raise HTTPException(422, "A destination path is required.")
        destination = validate_target_path(req.destination)
        _grant_for(destination.parent, "create", state)
        if destination.exists():
            raise HTTPException(409, "The destination already exists; nothing was overwritten.")
        try:
            _move_without_overwrite(path, destination)
        except FileExistsError as exc:
            raise HTTPException(409, "The destination already exists; nothing was overwritten.") from exc
        return {"action": req.action, "path": str(path), "destination": str(destination), "status": "completed"}

    if req.action == "delete":
        _grant_for(path, "delete", state)
        if not path.is_file():
            raise HTTPException(400, "Only individual files can be sent to quarantine; directory deletion is disabled.")
        quarantine = path.parent / ".laz-helper-quarantine"
        if quarantine.is_symlink():
            raise HTTPException(403, "A symbolic link cannot be used as the quarantine folder.")
        if quarantine.exists() and not quarantine.is_dir():
            raise HTTPException(403, "The quarantine path is not a folder.")
        ensure_no_symlink_components(quarantine)
        if is_protected(quarantine):
            raise HTTPException(403, "This location cannot be used for quarantine.")
        quarantine.mkdir(mode=0o700, exist_ok=True)
        target = quarantine / (secrets.token_hex(5) + "-" + path.name)
        _move_without_overwrite(path, target)
        return {"action": "delete", "path": str(path), "quarantined_as": str(target), "status": "quarantined"}

    raise HTTPException(422, "Unsupported operation.")


app = FastAPI(title=APP_NAME, version=__version__, docs_url=None, redoc_url=None)
router = APIRouter(prefix="/v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins()),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=300,
)


@app.middleware("http")
async def private_network_access_headers(request: Request, call_next):
    response = await call_next(request)
    if request.headers.get("origin", "").rstrip("/") in allowed_origins():
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class PairRequest(BaseModel):
    code: str | None = Field(default=None, min_length=7, max_length=7)


class PreferenceRequest(BaseModel):
    scope_mode: str | None = None
    approval_mode: str | None = None


class PickRequest(BaseModel):
    kind: Literal["folder", "file"]
    capabilities: list[str] = Field(min_length=1, max_length=6)


class OperationRequest(BaseModel):
    action: Literal["create", "edit", "move", "rename", "delete"]
    path: str = Field(min_length=1, max_length=4096)
    destination: str | None = Field(default=None, max_length=4096)
    content: str | None = Field(default=None, max_length=200_000)
    approved: bool = False


@router.get("/health")
async def health():
    return {"status": "ok", "app": APP_NAME, "version": __version__, "identity": "laz-helper-local-connector", "pairing_required": True}


@router.post("/pair")
async def pair(req: PairRequest, request: Request):
    origin = _origin(request)
    now = time.monotonic()
    attempts, reset = _pair_attempts.get(origin, (0, now + 300))
    if now > reset:
        attempts, reset = 0, now + 300
    if attempts >= 8:
        raise HTTPException(429, "Too many pairing attempts. Restart the connector and try again.")
    _pair_attempts[origin] = (attempts + 1, reset)
    current = store.snapshot().get("pairing_code", "")
    if req.code:
        if not hmac.compare_digest(req.code.strip().upper(), current.upper()):
            _record("pair", "denied", f"Pairing rejected for {origin}")
            raise HTTPException(401, "That pairing code is incorrect or has already been used.")
    else:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            try:
                accepted = messagebox.askyesno(
                    "Laz Helper device connection",
                    f"Allow the Laz Helper website at {origin} to connect to this local connector? Only grant access to folders/files you choose afterward.",
                    parent=root,
                )
            finally:
                root.destroy()
        except Exception as exc:
            raise HTTPException(501, "Native confirmation is unavailable. Enter the one-time pairing code shown in the connector terminal.") from exc
        if not accepted:
            _record("pair", "denied", f"Local pairing approval declined for {origin}")
            raise HTTPException(403, "Device pairing was cancelled on this computer.")
    token = secrets.token_urlsafe(32)
    def save(state):
        state.setdefault("paired_origins", {})[origin] = token
        state["pairing_code"] = new_pairing_code()
    store.update(save)
    _record("pair", "completed", f"Browser paired with {origin}")
    print(f"[Laz Connector] Paired with {origin}. New recovery code: {store.snapshot()['pairing_code']}", flush=True)
    return {"paired": True, "token": token, "origin": origin, "message": "Device connected."}


@router.get("/connection")
async def connection(origin: str = Depends(_auth)):
    state = _state()
    return {"connected": True, "app": APP_NAME, "version": __version__, "scope_mode": state["scope_mode"], "approval_mode": state["approval_mode"], "grant_count": len(state["grants"])}


@router.get("/permissions")
async def permissions(origin: str = Depends(_auth)):
    state = _state()
    return {"scope_mode": state["scope_mode"], "approval_mode": state["approval_mode"], "capabilities": sorted(CAPABILITIES), "grants": [_public_grant(g) for g in state["grants"]]}


@router.put("/permissions/preferences")
async def update_preferences(req: PreferenceRequest, origin: str = Depends(_auth)):
    state = _state()
    scope = req.scope_mode or state["scope_mode"]
    approval = req.approval_mode or state["approval_mode"]
    if scope not in SCOPE_MODES or approval not in APPROVAL_MODES:
        raise HTTPException(422, "Choose a supported permission scope and approval mode.")
    store.update(lambda s: s.update({"scope_mode": scope, "approval_mode": approval}))
    _record("permissions", "updated", f"Scope={scope}; approval={approval}")
    return {"scope_mode": scope, "approval_mode": approval}


@router.post("/permissions/pick")
async def pick_permission(req: PickRequest, origin: str = Depends(_auth)):
    if not req.capabilities or set(req.capabilities) - CAPABILITIES:
        raise HTTPException(422, "Choose one or more supported capabilities.")
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            selected = filedialog.askdirectory(title="Choose a folder for Laz Helper") if req.kind == "folder" else filedialog.askopenfilename(title="Choose a file for Laz Helper")
        finally:
            root.destroy()
    except Exception as exc:
        raise HTTPException(501, "The native picker is unavailable here. Run the connector in a graphical desktop session.") from exc
    if not selected:
        return {"cancelled": True}
    try:
        path = validate_existing_path(selected, req.kind)
    except (UnsafePath, PermissionDenied) as exc:
        _raise_path_error(exc)
    grant = {"id": secrets.token_hex(8), "label": path.name or str(path), "kind": req.kind, "path": str(path), "capabilities": sorted(set(req.capabilities)), "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    store.update(lambda s: s.setdefault("grants", []).append(grant))
    _record("grant", "created", f"{req.kind} grant added for {path}")
    return {"cancelled": False, "grant": _public_grant(grant)}


@router.delete("/permissions/grants/{grant_id}")
async def revoke_grant(grant_id: str, origin: str = Depends(_auth)):
    state = _state()
    matches = [g for g in state["grants"] if g.get("id") == grant_id]
    if not matches:
        raise HTTPException(404, "Permission grant not found.")
    store.update(lambda s: s.update({"grants": [g for g in s["grants"] if g.get("id") != grant_id]}))
    _record("grant", "revoked", f"Permission grant revoked: {matches[0].get('label', grant_id)}")
    return {"revoked": True, "grant_id": grant_id}


@router.get("/activity")
async def activity(limit: int = Query(default=50, ge=1, le=200), origin: str = Depends(_auth)):
    return {"items": list(reversed(_state().get("activity", [])[-limit:]))}


@router.get("/files")
async def list_files(path: str = Query(min_length=1, max_length=4096), approved: bool = False, origin: str = Depends(_auth)):
    state = _state()
    if state.get("scope_mode") == "ask_every_time" and not approved:
        raise HTTPException(409, "Reading this folder needs explicit approval.")
    try:
        folder = validate_existing_path(path, "folder")
        _grant_for(folder, "read", state)
    except (UnsafePath, PermissionDenied) as exc:
        _raise_path_error(exc)
    rows = []
    try:
        for item in sorted(folder.iterdir(), key=lambda p: p.name.casefold())[:1000]:
            if item.is_symlink():
                continue
            try:
                resolved = item.resolve(strict=True)
                _grant_for(resolved, "read", _state())
                stat = item.stat(follow_symlinks=False)
            except (OSError, UnsafePath, PermissionDenied):
                continue
            rows.append({"name": item.name, "path": str(item), "kind": "folder" if item.is_dir() else "file", "size_bytes": stat.st_size if item.is_file() else None, "modified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime))})
    except OSError as exc:
        raise HTTPException(400, "Could not read this folder.") from exc
    _record("list", "completed", f"Listed local folder {folder}")
    return {"path": str(folder), "items": rows}


@router.get("/files/content")
async def read_file_content(path: str = Query(min_length=1, max_length=4096), approved: bool = False, origin: str = Depends(_auth)):
    state = _state()
    if state.get("scope_mode") == "ask_every_time" and not approved:
        raise HTTPException(409, "Reading this file needs explicit approval.")
    try:
        file_path = validate_existing_path(path, "file")
        _grant_for(file_path, "read", state)
    except (UnsafePath, PermissionDenied) as exc:
        _raise_path_error(exc)
    if file_path.stat().st_size > 200_000:
        raise HTTPException(413, "This file is too large for the bounded text preview.")
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeError, OSError) as exc:
        raise HTTPException(415, "This file is not readable as UTF-8 text.") from exc
    _record("read", "completed", f"Read text from {file_path.name}")
    return {"path": str(file_path), "content": content}


@router.get("/duplicates")
async def find_duplicates(path: str = Query(min_length=1, max_length=4096), approved: bool = False, origin: str = Depends(_auth)):
    state = _state()
    if state.get("scope_mode") == "ask_every_time" and not approved:
        raise HTTPException(409, "Duplicate scanning reads local files and needs explicit approval.")
    try:
        folder = validate_existing_path(path, "folder")
        _grant_for(folder, "read", state)
    except (UnsafePath, PermissionDenied) as exc:
        _raise_path_error(exc)

    candidates: dict[int, list[Path]] = {}
    seen = 0
    total_bytes = 0
    truncated = False
    try:
        root_depth = len(folder.parts)
        for current, directories, names in os.walk(folder, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.parts) - root_depth
            if depth >= 8:
                directories[:] = []
            else:
                directories[:] = [name for name in directories if name != ".laz-helper-quarantine" and not (current_path / name).is_symlink() and not is_protected(current_path / name)]
            for name in names:
                item = current_path / name
                if item.is_symlink():
                    continue
                try:
                    _grant_for(item, "read", state)
                    info = item.stat(follow_symlinks=False)
                except (OSError, PermissionDenied, UnsafePath):
                    continue
                if not item.is_file() or info.st_size > 50 * 1024 * 1024:
                    continue
                if seen >= 500 or total_bytes + info.st_size > 250 * 1024 * 1024:
                    truncated = True
                    break
                seen += 1
                total_bytes += info.st_size
                candidates.setdefault(info.st_size, []).append(item)
            if truncated:
                break
    except OSError as exc:
        raise HTTPException(400, "Could not scan the selected folder for duplicates.") from exc

    groups = []
    for size, paths in candidates.items():
        if len(paths) < 2:
            continue
        hashes: dict[str, list[str]] = {}
        for item in paths:
            digest = hashlib.sha256()
            try:
                with item.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError:
                continue
            hashes.setdefault(digest.hexdigest(), []).append(str(item))
        for digest, matching in hashes.items():
            if len(matching) > 1:
                groups.append({"sha256": digest, "size_bytes": size, "count": len(matching), "files": matching})
    _record("duplicates", "completed", f"Read-only duplicate scan in {folder}; groups={len(groups)}")
    return {"folder": str(folder), "groups": groups, "files_checked": seen, "truncated": truncated, "read_only": True, "message": "Duplicate matches are review signals only; no files were changed."}


@router.post("/operations/preview")
async def preview_operation(req: OperationRequest, origin: str = Depends(_auth)):
    state = _state()
    try:
        path = validate_existing_path(req.path) if req.action in {"edit", "move", "rename", "delete"} else validate_target_path(req.path)
        capability = {"create": "create", "edit": "edit", "move": "move", "rename": "rename", "delete": "delete"}[req.action]
        if req.action == "create":
            _grant_for(path.parent, capability, state)
            if path.exists():
                raise HTTPException(409, "A file already exists at that destination.")
        else:
            _grant_for(path, capability, state)
        if req.action in {"move", "rename"}:
            if not req.destination:
                raise HTTPException(422, "A destination path is required.")
            destination = validate_target_path(req.destination)
            _grant_for(destination.parent, "create", state)
            if destination.exists():
                raise HTTPException(409, "The destination already exists.")
        requires_approval = _needs_approval(req.action, state)
        return {"action": req.action, "path": str(path), "destination": req.destination, "requires_approval": requires_approval, "would_change_files": True, "message": "Review the operation and confirm before applying it." if requires_approval else "This routine operation is covered by your current auto-approval preference."}
    except (UnsafePath, PermissionDenied) as exc:
        _raise_path_error(exc)


@router.post("/operations/execute")
async def execute_operation(req: OperationRequest, origin: str = Depends(_auth)):
    state = _state()
    if _needs_approval(req.action, state) and not req.approved:
        _record(req.action, "approval-required", f"Operation blocked pending approval: {Path(req.path).name}")
        raise HTTPException(409, "This action needs explicit approval before it can run.")
    try:
        result = _apply_operation(req, state)
    except (UnsafePath, PermissionDenied) as exc:
        _record(req.action, "denied", f"{req.action} denied for {Path(req.path).name}")
        _raise_path_error(exc)
    except HTTPException as exc:
        _record(req.action, "failed", f"{req.action} failed for {Path(req.path).name}: {exc.detail}")
        raise
    _record(req.action, result["status"], f"{req.action}: {Path(req.path).name}")
    return result


app.include_router(router)


def run():
    host = os.environ.get("LAZ_CONNECTOR_HOST", "127.0.0.1").strip()
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Laz Connector must bind to loopback (127.0.0.1, localhost, or ::1) only.")
    try:
        port = int(os.environ.get("LAZ_CONNECTOR_PORT", str(DEFAULT_PORT)))
    except ValueError as exc:
        raise SystemExit("LAZ_CONNECTOR_PORT must be an integer.") from exc
    if not 1024 <= port <= 65535:
        raise SystemExit("LAZ_CONNECTOR_PORT must be between 1024 and 65535.")
    state = store.snapshot()
    print(f"{APP_NAME} {__version__} listening at http://{host}:{port}", flush=True)
    print(f"Allowed website origins: {', '.join(sorted(allowed_origins()))}", flush=True)
    print(f"One-time pairing code: {state['pairing_code']}", flush=True)
    print("Keep this process running. Do not expose the connector port to a network.", flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run()
