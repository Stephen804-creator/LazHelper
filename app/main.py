from contextlib import asynccontextmanager
import asyncio
from pathlib import Path
import zipfile

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .models import ScanRequest, AnalyzeRequest
from .scanner import scan_folder, safe_file_path, UnsafePath
from .extractor import extract_file
from .ai_engine import recommend, AIUnavailable
from . import organizer, sloth_mode, insights, workspace_intelligence

STATIC = Path(__file__).resolve().parent.parent / "static"

@asynccontextmanager
async def lifespan(app):
    config.ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    stop = asyncio.Event()
    task = asyncio.create_task(sloth_mode.scheduler_loop(stop))
    app.state.sloth_stop = stop
    try:
        yield
    finally:
        stop.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="LazHelper",
    version="0.2.0",
    description="Local-first file understanding assistant with review-first organisation",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

class PlanRequest(BaseModel):
    relative_paths: list[str] = Field(min_length=1, max_length=500)

class ApplyItem(BaseModel):
    source: str
    destination: str
    approved: bool = False

class ApplyRequest(BaseModel):
    items: list[ApplyItem] = Field(min_length=1, max_length=500)

class DuplicateRequest(BaseModel):
    relative_path: str = "."

class PreferencesRequest(BaseModel):
    category_rules: dict[str, list[str]] | None = None
    keep_originals: bool | None = None
    review_all_moves: bool | None = None
    include_date_in_plan: bool | None = None

class QueueDecision(BaseModel):
    path: str
    decision: str

@app.get("/")
async def home():
    return FileResponse(STATIC / "index.html")

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "LazHelper", "read_only": False,
            "safety": "Moves require explicit approval; no delete endpoint exists."}

@app.get("/api/config")
async def get_config():
    return {"workspace_label": "Configured workspace", "workspace_ready": config.ALLOWED_ROOT.exists(),
            "ai_model": config.OLLAMA_MODEL, "safety": "Review-first moves; no overwrites or deletes."}

@app.post("/api/scan")
async def scan(req: ScanRequest):
    try:
        return scan_folder(req.relative_path)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        path = safe_file_path(req.relative_path)
        extracted = extract_file(req.relative_path)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        raise HTTPException(422, str(exc)) from exc
    rec = None
    ai_status = "unavailable"
    message = "Content extracted. Start Ollama and pull the configured model for an AI recommendation."
    try:
        rec = await recommend(path.name, extracted["text"], extracted["details"])
        ai_status, message = "ready", "Recommendation generated. Review it before taking action."
    except AIUnavailable as exc:
        message = str(exc)
    return {"relative_path": req.relative_path, "name": path.name, "kind": extracted["kind"],
            "details": extracted["details"], "extracted_text": extracted["text"],
            "ai_status": ai_status, "recommendation": rec, "message": message, "files_changed": False}

@app.post("/api/organize/plan")
async def organize_plan(req: PlanRequest):
    try:
        return organizer.build_plan(req.relative_paths)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/api/organize/apply")
async def organize_apply(req: ApplyRequest):
    try:
        return organizer.apply_plan([item.model_dump() for item in req.items])
    except (UnsafePath, ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/api/duplicates")
async def duplicates(req: DuplicateRequest):
    try:
        return organizer.find_duplicates(req.relative_path)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

@app.get("/api/review-queue")
async def review_queue():
    return {"items": organizer.list_queue()}

@app.post("/api/review-queue/decision")
async def review_queue_decision(req: QueueDecision):
    try:
        # Confirm that queue paths still resolve inside the workspace before updating state.
        safe_file_path(req.path)
        return organizer.resolve_queue_item(req.path, req.decision)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/api/journal")
async def journal():
    return {"operations": organizer.list_journal()}

@app.post("/api/journal/{operation_id}/undo")
async def undo(operation_id: int):
    try:
        return organizer.undo_operation(operation_id)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc

@app.get("/api/preferences")
async def get_preferences():
    return organizer.get_preferences()

@app.put("/api/preferences")
async def update_preferences(req: PreferencesRequest):
    try:
        payload = req.model_dump(exclude_none=True)
        return organizer.save_preferences(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

class SlothSettingsRequest(BaseModel):
    enabled: bool | None = None
    inbox: str | None = None
    interval_minutes: int | None = Field(default=None, ge=15, le=1440)

class InsightsRequest(BaseModel):
    relative_path: str = "."

@app.get("/api/sloth-mode")
async def get_sloth_mode():
    return sloth_mode.settings()

@app.put("/api/sloth-mode")
async def update_sloth_mode(req: SlothSettingsRequest):
    try:
        payload = req.model_dump(exclude_none=True)
        return sloth_mode.configure(payload)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.post("/api/sloth-mode/run")
async def run_sloth_mode():
    try:
        return await asyncio.to_thread(sloth_mode.run_once)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/api/insights")
async def get_insights(relative_path: str = "."):
    try:
        return await asyncio.to_thread(insights.workspace_insights, relative_path)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

# Stages A–E: explainable workspace intelligence. All endpoints are read-only.
async def _run_intelligence(function, *args):
    try:
        return await asyncio.to_thread(function, *args)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/relationships")
async def get_relationships(relative_path: str = ".", max_files: int = 400):
    if not 1 <= max_files <= 1000:
        raise HTTPException(422, "max_files must be between 1 and 1000.")
    return await _run_intelligence(workspace_intelligence.file_relationships, relative_path, max_files)


@app.post("/api/duplicates/insights")
async def get_duplicate_insights(req: DuplicateRequest):
    return await _run_intelligence(workspace_intelligence.duplicate_insights, req.relative_path)


@app.get("/api/search")
async def search_workspace(query: str = "", relative_path: str = ".", max_results: int = 50):
    if not 1 <= max_results <= 100:
        raise HTTPException(422, "max_results must be between 1 and 100.")
    return await _run_intelligence(workspace_intelligence.content_search, query, relative_path, max_results)


@app.get("/api/knowledge-map")
async def get_knowledge_map(relative_path: str = ".", max_files: int = 250):
    if not 1 <= max_files <= 1000:
        raise HTTPException(422, "max_files must be between 1 and 1000.")
    return await _run_intelligence(workspace_intelligence.knowledge_map, relative_path, max_files)


@app.get("/api/health-report")
async def get_workspace_health_report(relative_path: str = ".", max_files: int = 500):
    if not 1 <= max_files <= 1000:
        raise HTTPException(422, "max_files must be between 1 and 1000.")
    return await _run_intelligence(workspace_intelligence.workspace_health_report, relative_path, max_files)

