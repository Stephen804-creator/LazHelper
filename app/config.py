from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def _path(name, default):
    value = Path(os.getenv(name, default)).expanduser()
    return (PROJECT_ROOT / value).resolve() if not value.is_absolute() else value.resolve()


ALLOWED_ROOT = _path("LAZHELPER_ALLOWED_ROOT", os.getenv("LAZYDESK_ALLOWED_ROOT", "./workspace"))
MAX_FILES = max(1, min(int(os.getenv("LAZHELPER_MAX_FILES", os.getenv("LAZYDESK_MAX_FILES", "1500"))), 10000))
MAX_DEPTH = max(0, min(int(os.getenv("LAZHELPER_MAX_DEPTH", os.getenv("LAZYDESK_MAX_DEPTH", "8"))), 30))
MAX_FILE_BYTES = max(1, min(int(os.getenv("LAZHELPER_MAX_FILE_MB", os.getenv("LAZYDESK_MAX_FILE_MB", "20"))), 100)) * 1024 * 1024
MAX_TEXT_CHARS = max(1000, min(int(os.getenv("LAZHELPER_MAX_TEXT_CHARS", os.getenv("LAZYDESK_MAX_TEXT_CHARS", "18000"))), 50000))

# Ollama Cloud accepts either https://ollama.com or https://ollama.com/api.
# Keep local Ollama usable for development when no cloud URL is configured.
OLLAMA_URL = os.getenv("LAZHELPER_OLLAMA_URL", os.getenv("LAZYDESK_OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
OLLAMA_MODEL = os.getenv("LAZHELPER_OLLAMA_MODEL", os.getenv("LAZYDESK_OLLAMA_MODEL", "gemma3:1b"))
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", os.getenv("LAZHELPER_OLLAMA_API_KEY", "")).strip()
AI_TIMEOUT_SECONDS = max(5, min(int(os.getenv("LAZHELPER_AI_TIMEOUT_SECONDS", os.getenv("LAZYDESK_AI_TIMEOUT_SECONDS", "45"))), 180))
