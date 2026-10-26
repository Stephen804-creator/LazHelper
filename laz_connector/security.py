"""Path confinement, grants, and protected-location checks for Laz Connector."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

CAPABILITIES = {"read", "create", "edit", "move", "rename", "delete"}
SCOPE_MODES = {"permitted_locations", "selected_folders", "selected_files", "ask_every_time"}
APPROVAL_MODES = {"ask_every_time", "routine_auto"}


class PermissionDenied(ValueError):
    pass


class UnsafePath(ValueError):
    pass


def _protected_roots() -> list[Path]:
    if os.name == "nt":
        roots = [
            Path(os.environ.get("WINDIR", r"C:\Windows")),
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            Path(os.environ.get("ProgramData", r"C:\ProgramData")),
        ]
    else:
        roots = [Path(p) for p in ("/etc", "/bin", "/sbin", "/usr", "/var", "/boot", "/proc", "/sys", "/dev", "/System", "/Library")]
    out = []
    for root in roots:
        try:
            out.append(root.resolve())
        except OSError:
            continue
    return out


def is_protected(path: Path) -> bool:
    try:
        candidate = path.resolve(strict=False)
    except OSError:
        return True
    if candidate == Path(candidate.anchor):
        return True
    for root in _protected_roots():
        try:
            candidate.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def ensure_no_symlink_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                raise UnsafePath("Symbolic links are not followed.")
        except OSError as exc:
            raise UnsafePath("Could not safely inspect the requested path.") from exc


def validate_existing_path(value: str, expected: str | None = None) -> Path:
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise UnsafePath("Choose an absolute path from the local device picker.")
    ensure_no_symlink_components(raw)
    try:
        path = raw.resolve(strict=True)
    except OSError as exc:
        raise UnsafePath("The selected path does not exist or is not accessible.") from exc
    if expected == "folder" and not path.is_dir():
        raise UnsafePath("Select a folder.")
    if expected == "file" and not path.is_file():
        raise UnsafePath("Select a file.")
    if is_protected(path):
        raise UnsafePath("This is a protected operating-system location.")
    return path


def validate_target_path(value: str) -> Path:
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise UnsafePath("Use an absolute path within a granted location.")
    ensure_no_symlink_components(raw)
    try:
        parent = raw.parent.resolve(strict=True)
    except OSError as exc:
        raise UnsafePath("The destination folder does not exist.") from exc
    if not parent.is_dir() or is_protected(parent):
        raise UnsafePath("The destination folder is not available for file operations.")
    target = parent / raw.name
    if target.name in {"", ".", ".."}:
        raise UnsafePath("Invalid destination name.")
    return target


def grant_matches(grant: dict, path: Path, capability: str) -> bool:
    if capability not in grant.get("capabilities", []):
        return False
    try:
        candidate = path.resolve(strict=False)
        root = Path(grant["path"]).resolve(strict=True)
        if grant.get("kind") == "file":
            return candidate == root
        candidate.relative_to(root)
        return True
    except (OSError, ValueError, KeyError):
        return False


def require_grant(grants: Iterable[dict], path: Path, capability: str, scope_mode: str) -> None:
    if capability not in CAPABILITIES:
        raise PermissionDenied("Unsupported permission capability.")
    allowed = any(grant_matches(g, path, capability) for g in grants)
    if scope_mode == "selected_folders":
        allowed = any(g.get("kind") == "folder" and grant_matches(g, path, capability) for g in grants)
    elif scope_mode == "selected_files":
        allowed = any(g.get("kind") == "file" and grant_matches(g, path, capability) for g in grants)
    if not allowed:
        raise PermissionDenied("No matching grant allows this action.")
    if is_protected(path):
        raise PermissionDenied("Protected operating-system locations cannot be accessed.")
