from pathlib import Path
import os
PROJECT_ROOT=Path(__file__).resolve().parent.parent
def _path(name,default):
 v=Path(os.getenv(name,default)).expanduser()
 return (PROJECT_ROOT/v).resolve() if not v.is_absolute() else v.resolve()
ALLOWED_ROOT=_path("LAZYDESK_ALLOWED_ROOT","./workspace")
MAX_FILES=max(1,min(int(os.getenv("LAZYDESK_MAX_FILES","1500")),10000))
MAX_DEPTH=max(0,min(int(os.getenv("LAZYDESK_MAX_DEPTH","8")),30))
MAX_FILE_BYTES=max(1,min(int(os.getenv("LAZYDESK_MAX_FILE_MB","20")),100))*1024*1024
MAX_TEXT_CHARS=max(1000,min(int(os.getenv("LAZYDESK_MAX_TEXT_CHARS","18000")),50000))
OLLAMA_URL=os.getenv("LAZYDESK_OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL=os.getenv("LAZYDESK_OLLAMA_MODEL","gemma3:1b")
AI_TIMEOUT_SECONDS=max(5,min(int(os.getenv("LAZYDESK_AI_TIMEOUT_SECONDS","45")),180))
