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
from . import organizer, sloth_mode, insights, workspace_intelligence, extended_workspace
from .stage_l import router as stage_l_router

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
app.include_router(stage_l_router)

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

class ArchiveInspectRequest(BaseModel):
    relative_path: str = Field(min_length=1, max_length=500)
    max_entries: int = Field(default=500, ge=1, le=1000)
    preview_text: bool = False

class ProjectWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: str = "study"
    description: str = Field(default="", max_length=1000)
    folder_path: str = Field(default=".", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=30)
    structure: list[str] = Field(default_factory=list, max_length=30)

class ProjectWorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    kind: str | None = None
    description: str | None = Field(default=None, max_length=1000)
    folder_path: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=30)
    structure: list[str] | None = Field(default=None, max_length=30)

class CommandPreviewRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    relative_path: str = Field(default=".", max_length=500)

class KnowledgeQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    relative_path: str = Field(default=".", max_length=500)
    max_sources: int = Field(default=5, ge=1, le=10)

class WorkflowStep(BaseModel):
    action: str
    parameters: dict = Field(default_factory=dict)

class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    steps: list[WorkflowStep] = Field(min_length=1, max_length=10)

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

# Stage F — recovery visibility and portable journal export.
@app.get("/api/recovery/history")
async def recovery_history(limit: int = 100, export_format: str = "json"):
    if not 1 <= limit <= 200:
        raise HTTPException(422, "limit must be between 1 and 200.")
    try:
        return extended_workspace.recovery_history(limit, export_format)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/api/recovery/inspect/{operation_id}")
async def recovery_inspect(operation_id: int):
    try:
        return extended_workspace.inspect_recovery(operation_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

# Stage G — project/study workspace profiles. These save metadata only.
@app.get("/api/projects")
async def list_project_workspaces():
    return extended_workspace.list_projects()

@app.post("/api/projects")
async def create_project_workspace(req: ProjectWorkspaceRequest):
    try:
        return await asyncio.to_thread(extended_workspace.create_project, req.model_dump())
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/api/projects/{project_id}")
async def get_project_workspace(project_id: int):
    try:
        return extended_workspace.get_project(project_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

@app.get("/api/projects/{project_id}/overview")
async def project_workspace_overview(project_id: int):
    try:
        return await asyncio.to_thread(extended_workspace.project_overview, project_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc

@app.put("/api/projects/{project_id}")
async def update_project_workspace(project_id: int, req: ProjectWorkspaceUpdate):
    try:
        payload = req.model_dump(exclude_none=True)
        return await asyncio.to_thread(extended_workspace.update_project, project_id, payload)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.delete("/api/projects/{project_id}")
async def delete_project_workspace(project_id: int):
    try:
        return extended_workspace.delete_project(project_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

# Stage H — bounded ZIP inventory; never extracts.
@app.post("/api/archive/inspect")
async def inspect_archive(req: ArchiveInspectRequest):
    try:
        return await asyncio.to_thread(extended_workspace.inspect_archive, req.relative_path, req.max_entries, req.preview_text)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        raise HTTPException(422, str(exc)) from exc

# Stage I — translate plain-language requests into safe, reviewable proposals.
@app.post("/api/commands/preview")
async def preview_workspace_command(req: CommandPreviewRequest):
    try:
        return extended_workspace.preview_command(req.command, req.relative_path)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

# Stage J — local evidence retrieval, not a general-purpose or cloud chatbot.
@app.post("/api/knowledge/ask")
async def ask_workspace_knowledge(req: KnowledgeQuestionRequest):
    try:
        return await asyncio.to_thread(extended_workspace.ask_local_knowledge, req.question, req.relative_path, req.max_sources)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

# Stage K — reusable, explicitly read-only workflows.
@app.get("/api/workflows")
async def list_saved_workflows():
    return extended_workspace.list_workflows()

@app.post("/api/workflows")
async def create_saved_workflow(req: WorkflowCreateRequest):
    try:
        return extended_workspace.create_workflow(req.model_dump())
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

@app.get("/api/workflows/{workflow_id}")
async def get_saved_workflow(workflow_id: int):
    try:
        return extended_workspace.get_workflow(workflow_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

@app.post("/api/workflows/{workflow_id}/run")
async def run_saved_workflow(workflow_id: int):
    try:
        return await asyncio.to_thread(extended_workspace.run_workflow, workflow_id)
    except UnsafePath as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@app.delete("/api/workflows/{workflow_id}")
async def delete_saved_workflow(workflow_id: int):
    try:
        return extended_workspace.delete_workflow(workflow_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

