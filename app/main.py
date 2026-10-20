from contextlib import asynccontextmanager
from pathlib import Path
import zipfile
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import config
from .models import ScanRequest,AnalyzeRequest
from .scanner import scan_folder,safe_file_path,UnsafePath
from .extractor import extract_file
from .ai_engine import recommend,AIUnavailable
STATIC=Path(__file__).resolve().parent.parent/"static"
@asynccontextmanager
async def lifespan(app):
 config.ALLOWED_ROOT.mkdir(parents=True,exist_ok=True)
 yield
app=FastAPI(title="LazyDesk",version="0.1.0",description="Local-first read-only file understanding assistant",lifespan=lifespan)
app.mount("/static",StaticFiles(directory=STATIC),name="static")
@app.get("/")
async def home(): return FileResponse(STATIC/"index.html")
@app.get("/api/health")
async def health(): return {"status":"ok","app":"LazyDesk","read_only":True}
@app.get("/api/config")
async def get_config(): return {"workspace_label":"Configured workspace","workspace_ready":config.ALLOWED_ROOT.exists(),"ai_model":config.OLLAMA_MODEL,"safety":"Read-only; files are never moved or deleted."}
@app.post("/api/scan")
async def scan(req:ScanRequest):
 try: return scan_folder(req.relative_path)
 except UnsafePath as exc: raise HTTPException(400,str(exc)) from exc
 except FileNotFoundError as exc: raise HTTPException(404,str(exc)) from exc
@app.post("/api/analyze")
async def analyze(req:AnalyzeRequest):
 try: path=safe_file_path(req.relative_path); extracted=extract_file(req.relative_path)
 except UnsafePath as exc: raise HTTPException(400,str(exc)) from exc
 except FileNotFoundError as exc: raise HTTPException(404,str(exc)) from exc
 except (ValueError,OSError,zipfile.BadZipFile) as exc: raise HTTPException(422,str(exc)) from exc
 rec=None; ai_status="unavailable"; message="Content extracted. Start Ollama and pull the configured model for an AI recommendation."
 try:
  rec=await recommend(path.name,extracted["text"],extracted["details"]); ai_status="ready"; message="Recommendation generated. Review it before taking action."
 except AIUnavailable as exc: message=str(exc)
 return {"relative_path":req.relative_path,"name":path.name,"kind":extracted["kind"],"details":extracted["details"],"extracted_text":extracted["text"],"ai_status":ai_status,"recommendation":rec,"message":message,"files_changed":False}
