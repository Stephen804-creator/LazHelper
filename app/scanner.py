"""Read-only workspace scanner with symlink-resistant path handling."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import errno
import os
import re
import stat

from . import config
from .models import FileRecord


SUPPORTED = {
    ".pdf": "PDF document", ".docx": "Word document",
    ".txt": "Text document", ".md": "Markdown document",
    ".rtf": "Rich Text document", ".csv": "CSV spreadsheet",
    ".xls": "Legacy Excel spreadsheet", ".xlsx": "Excel spreadsheet",
    ".pptx": "PowerPoint presentation", ".png": "Image metadata",
    ".jpg": "Image metadata", ".jpeg": "Image metadata",
    ".webp": "Image metadata", ".zip": "ZIP inventory only",
    ".py": "Source code (text only)", ".js": "Source code (text only)",
    ".ts": "Source code (text only)", ".html": "Text/source (not executed)",
    ".css": "Source code (text only)", ".json": "Structured text",
    ".xml": "Structured text", ".yaml": "Structured text",
    ".yml": "Structured text", ".toml": "Structured text",
    ".java": "Source code (text only)", ".c": "Source code (text only)",
    ".h": "Source code (text only)", ".cpp": "Source code (text only)",
    ".go": "Source code (text only)", ".rs": "Source code (text only)",
    ".sh": "Script (text only)", ".sql": "SQL source (text only)",
}


class UnsafePath(ValueError):
    pass


def _validate_relative(value: str | Path) -> Path:
    raw = str(value or ".")
    if (
        "\x00" in raw
        or "\\" in raw
        or raw.startswith("/")
        or re.match(r"^[a-zA-Z]:", raw)
    ):
        raise UnsafePath("Use a relative workspace path with forward slashes.")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise UnsafePath("Use a relative path inside the configured workspace.")
    return path


def _root() -> Path:
    root = config.ALLOWED_ROOT.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError("Configured workspace folder not found.")
    return root


def safe_workspace_path(relative_path=".") -> Path:
    root = _root()
    part = _validate_relative(relative_path)
    current = root
    for name in part.parts:
        if name in ("", "."):
            continue
        current = current / name
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            raise FileNotFoundError("Workspace folder not found.") from None
        if stat.S_ISLNK(mode):
            raise UnsafePath("Symlinks are not followed.")
    target = (root / part).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise UnsafePath("Path is outside the configured workspace.") from exc
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError("Workspace folder not found.")
    return target


def safe_file_path(relative_path) -> Path:
    root = _root()
    part = _validate_relative(relative_path)
    if not part.parts or str(part) == ".":
        raise FileNotFoundError("File not found in workspace.")
    current = root
    for name in part.parts:
        if name in ("", "."):
            continue
        current = current / name
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            raise FileNotFoundError("File not found in workspace.") from None
        if stat.S_ISLNK(mode):
            raise UnsafePath("Symlinks are not followed.")
    target = (root / part).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise UnsafePath("File is outside the configured workspace.") from exc
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("File not found in workspace.")
    return target


def _open_directory_fd(relative_path="."):
    """Open a workspace directory component-by-component without following symlinks."""
    part = _validate_relative(relative_path)
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        path = safe_workspace_path(relative_path)
        return os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))

    root = _root()
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    current_fd = root_fd
    try:
        for name in part.parts:
            if name in ("", "."):
                continue
            try:
                next_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current_fd,
                )
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise UnsafePath("Symlinks are not followed.") from error
                raise
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        result = current_fd
        if result == root_fd:
            root_fd = -1
        else:
            os.close(root_fd)
            root_fd = -1
        current_fd = -1
        return result
    finally:
        if current_fd >= 0 and current_fd != root_fd:
            os.close(current_fd)
        if root_fd >= 0:
            os.close(root_fd)


@contextmanager
def open_workspace_directory(relative_path="."):
    fd = _open_directory_fd(relative_path)
    try:
        yield fd
    finally:
        os.close(fd)


def open_workspace_file(relative_path):
    """Open a regular workspace file without following symlinks.

    POSIX systems use openat-style directory descriptors and O_NOFOLLOW for every
    path component. Other platforms use a before/after inode check as a fallback.
    """
    part = _validate_relative(relative_path)
    if not part.parts or str(part) == ".":
        raise FileNotFoundError("File not found in workspace.")

    if os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"):
        parent_fd = _open_directory_fd(Path(*part.parts[:-1]) if len(part.parts) > 1 else ".")
        try:
            try:
                fd = os.open(
                    part.parts[-1],
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=parent_fd,
                )
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise UnsafePath("Symlinks are not followed.") from error
                raise
        finally:
            os.close(parent_fd)
    else:
        path = safe_file_path(relative_path)
        before = path.lstat()
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        after = os.fstat(fd)
        if (
            not stat.S_ISREG(after.st_mode)
            or before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
        ):
            os.close(fd)
            raise UnsafePath("File changed while it was being opened.")

    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise UnsafePath("Only regular files can be inspected.")
        if info.st_size > config.MAX_FILE_BYTES:
            raise ValueError("File exceeds configured size limit.")
        return os.fdopen(fd, "rb")
    except Exception:
        os.close(fd)
        raise


def ensure_workspace_directory(relative_path):
    """Create missing workspace directories without traversing symlinks (POSIX)."""
    part = _validate_relative(relative_path)
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        root = _root()
        target = root
        for name in part.parts:
            if name in ("", "."):
                continue
            target = target / name
            if target.is_symlink():
                raise UnsafePath("Symlinks are not followed.")
            if target.exists() and not target.is_dir():
                raise UnsafePath("A workspace path component is not a directory.")
            target.mkdir(exist_ok=True)
        return target

    root_fd = os.open(_root(), os.O_RDONLY | os.O_DIRECTORY)
    current_fd = root_fd
    try:
        for name in part.parts:
            if name in ("", "."):
                continue
            try:
                next_fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current_fd,
                )
            except FileNotFoundError:
                os.mkdir(name, mode=0o700, dir_fd=current_fd)
                try:
                    next_fd = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=current_fd,
                    )
                except OSError as error:
                    if error.errno == errno.ELOOP:
                        raise UnsafePath("Symlinks are not followed.") from error
                    raise
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise UnsafePath("Symlinks are not followed.") from error
                raise
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        if current_fd != root_fd:
            os.close(current_fd)
            current_fd = root_fd
        return _root() / part
    finally:
        if current_fd >= 0 and current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


@contextmanager
def create_workspace_file(relative_path):
    """Create a new file exclusively inside the workspace; never follow a link."""
    part = _validate_relative(relative_path)
    if not part.parts or str(part) == ".":
        raise UnsafePath("A destination file name is required.")
    parent = Path(*part.parts[:-1]) if len(part.parts) > 1 else Path(".")
    if os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"):
        parent_fd = _open_directory_fd(parent)
        try:
            try:
                fd = os.open(
                    part.parts[-1],
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=parent_fd,
                )
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise UnsafePath("Destination must not be a symlink.") from error
                raise
        finally:
            os.close(parent_fd)
        with os.fdopen(fd, "wb") as stream:
            yield stream
    else:
        target = _root() / part
        if target.exists() or target.is_symlink():
            raise FileExistsError("Destination already exists.")
        with target.open("xb") as stream:
            yield stream


def unlink_workspace_file(relative_path, expected_stat):
    """Unlink only the same regular file that was opened earlier."""
    part = _validate_relative(relative_path)
    if not part.parts or str(part) == ".":
        raise UnsafePath("A file path is required.")
    parent = Path(*part.parts[:-1]) if len(part.parts) > 1 else Path(".")
    if os.name == "posix" and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"):
        parent_fd = _open_directory_fd(parent)
        try:
            current = os.stat(
                part.parts[-1],
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(current.st_mode)
                or current.st_dev != expected_stat.st_dev
                or current.st_ino != expected_stat.st_ino
            ):
                raise UnsafePath("File changed before it could be moved.")
            os.unlink(part.parts[-1], dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
    else:
        target = safe_file_path(relative_path)
        current = target.lstat()
        if (
            current.st_dev != expected_stat.st_dev
            or current.st_ino != expected_stat.st_ino
        ):
            raise UnsafePath("File changed before it could be moved.")
        target.unlink()


def scan_folder(relative_path="."):
    folder = safe_workspace_path(relative_path)
    base = _root()
    root_rel = folder.relative_to(base).as_posix()
    if root_rel == ".":
        root_rel = ""

    found = []
    skipped = 0
    truncated = False
    stack = [(root_rel, 0)]

    while stack:
        current_rel, depth = stack.pop()
        try:
            with open_workspace_directory(current_rel or ".") as directory_fd:
                with os.scandir(directory_fd) as entries:
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                skipped += 1
                                continue
                            child_rel = (
                                f"{current_rel}/{entry.name}"
                                if current_rel else entry.name
                            )
                            if entry.is_dir(follow_symlinks=False):
                                if depth < config.MAX_DEPTH:
                                    stack.append((child_rel, depth + 1))
                                else:
                                    skipped += 1
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                skipped += 1
                                continue

                            info = entry.stat(follow_symlinks=False)
                            ext = Path(entry.name).suffix.lower()
                            found.append(FileRecord(
                                relative_path=child_rel,
                                name=entry.name,
                                extension=ext,
                                size_bytes=info.st_size,
                                modified_at=datetime.fromtimestamp(
                                    info.st_mtime, timezone.utc
                                ).isoformat(),
                                detected_type=SUPPORTED.get(
                                    ext, "Unsupported or unknown file type"
                                ),
                                readable=(
                                    ext in SUPPORTED
                                    and info.st_size <= config.MAX_FILE_BYTES
                                ),
                                note=(
                                    "File exceeds configured size limit"
                                    if info.st_size > config.MAX_FILE_BYTES
                                    else None
                                ),
                            ))
                            if len(found) >= config.MAX_FILES:
                                truncated = True
                                stack.clear()
                                break
                        except (OSError, ValueError):
                            skipped += 1
        except (OSError, UnsafePath):
            skipped += 1

    found.sort(key=lambda item: item.relative_path.casefold())
    return {
        "workspace_label": "Configured workspace",
        "scanned_root": root_rel or ".",
        "files": found,
        "total_files": len(found),
        "truncated": truncated,
        "skipped": skipped,
        "message": "Read-only scan complete. No files were changed.",
    }
