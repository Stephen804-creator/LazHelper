from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def _setting(name: str, default: str, legacy_name: str | None = None) -> str:
    """Prefer the current Laz Helper setting while preserving older deployments."""
    if name in os.environ:
        return os.environ[name]
    if legacy_name and legacy_name in os.environ:
        return os.environ[legacy_name]
    return default


def _path(name: str, default: str, legacy_name: str | None = None) -> Path:
    value = Path(_setting(name, default, legacy_name)).expanduser()
    return (PROJECT_ROOT / value).resolve() if not value.is_absolute() else value.resolve()


ALLOWED_ROOT = _path("LAZ_HELPER_ALLOWED_ROOT", "./workspace", "LAZYDESK_ALLOWED_ROOT")
MAX_FILES = max(1, min(int(_setting("LAZ_HELPER_MAX_FILES", "1500", "LAZYDESK_MAX_FILES")), 10000))
MAX_DEPTH = max(0, min(int(_setting("LAZ_HELPER_MAX_DEPTH", "8", "LAZYDESK_MAX_DEPTH")), 30))
MAX_FILE_BYTES = max(1, min(int(_setting("LAZ_HELPER_MAX_FILE_MB", "20", "LAZYDESK_MAX_FILE_MB")), 100)) * 1024 * 1024
MAX_TEXT_CHARS = max(1000, min(int(_setting("LAZ_HELPER_MAX_TEXT_CHARS", "18000", "LAZYDESK_MAX_TEXT_CHARS")), 50000))
OLLAMA_URL = _setting("LAZ_HELPER_OLLAMA_URL", "http://127.0.0.1:11434", "LAZYDESK_OLLAMA_URL").rstrip("/")
OLLAMA_MODEL = _setting("LAZ_HELPER_OLLAMA_MODEL", "gemma3:1b", "LAZYDESK_OLLAMA_MODEL")
AI_TIMEOUT_SECONDS = max(5, min(int(_setting("LAZ_HELPER_AI_TIMEOUT_SECONDS", "45", "LAZYDESK_AI_TIMEOUT_SECONDS")), 180))
