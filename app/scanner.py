"""Read-only scanner; all paths are confined to the configured workspace."""
from datetime import datetime,timezone
from pathlib import Path
import os
from . import config
from .models import FileRecord
SUPPORTED={".pdf":"PDF document",".docx":"Word document",".txt":"Text document",".md":"Markdown document",".rtf":"Rich Text document",".csv":"CSV spreadsheet",".xls":"Legacy Excel spreadsheet",".xlsx":"Excel spreadsheet",".pptx":"PowerPoint presentation",".png":"Image metadata",".jpg":"Image metadata",".jpeg":"Image metadata",".webp":"Image metadata",".zip":"ZIP inventory only",".py":"Source code (text only)",".js":"Source code (text only)",".ts":"Source code (text only)",".html":"Text/source (not executed)",".css":"Source code (text only)",".json":"Structured text",".xml":"Structured text",".yaml":"Structured text",".yml":"Structured text",".toml":"Structured text",".java":"Source code (text only)",".c":"Source code (text only)",".h":"Source code (text only)",".cpp":"Source code (text only)",".go":"Source code (text only)",".rs":"Source code (text only)",".sh":"Script (text only)",".sql":"SQL source (text only)"}
class UnsafePath(ValueError): pass
def _validate_relative(value):
 p=Path(value or ".")
 if p.is_absolute() or ".." in p.parts: raise UnsafePath("Use a relative path inside the configured workspace.")
 return p
def safe_workspace_path(relative_path="."):
 root=config.ALLOWED_ROOT.resolve(); part=_validate_relative(relative_path); cur=root
 for name in part.parts:
  if name in ("","."): continue
  cur=cur/name
  if cur.is_symlink(): raise UnsafePath("Symlinks are not followed.")
 target=(root/part).resolve()
 try: target.relative_to(root)
 except ValueError as exc: raise UnsafePath("Path is outside the configured workspace.") from exc
 if not target.exists() or not target.is_dir(): raise FileNotFoundError("Workspace folder not found.")
 return target
def safe_file_path(relative_path):
 root=config.ALLOWED_ROOT.resolve(); part=_validate_relative(relative_path); cur=root
 for name in part.parts:
  if name in ("","."): continue
  cur=cur/name
  if cur.is_symlink(): raise UnsafePath("Symlinks are not followed.")
 target=(root/part).resolve()
 try: target.relative_to(root)
 except ValueError as exc: raise UnsafePath("File is outside the configured workspace.") from exc
 if not target.exists() or not target.is_file(): raise FileNotFoundError("File not found in workspace.")
 return target
def scan_folder(relative_path="."):
 folder=safe_workspace_path(relative_path); base=config.ALLOWED_ROOT.resolve()
 found=[]; skipped=0; truncated=False; stack=[(folder,0)]
 while stack:
  current,depth=stack.pop()
  try:
   with os.scandir(current) as entries:
    for entry in entries:
     try:
      if entry.is_symlink(): skipped+=1; continue
      if entry.is_dir(follow_symlinks=False):
       if depth<config.MAX_DEPTH: stack.append((Path(entry.path),depth+1))
       else: skipped+=1
       continue
      if not entry.is_file(follow_symlinks=False): skipped+=1; continue
      p=Path(entry.path); stat=entry.stat(follow_symlinks=False); ext=p.suffix.lower()
      found.append(FileRecord(relative_path=p.relative_to(base).as_posix(),name=p.name,extension=ext,size_bytes=stat.st_size,modified_at=datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),detected_type=SUPPORTED.get(ext,"Unsupported or unknown file type"),readable=ext in SUPPORTED and stat.st_size<=config.MAX_FILE_BYTES,note="File exceeds configured size limit" if stat.st_size>config.MAX_FILE_BYTES else None))
      if len(found)>=config.MAX_FILES: truncated=True; stack.clear(); break
     except (OSError,ValueError): skipped+=1
  except OSError: skipped+=1
 found.sort(key=lambda f:f.relative_path.casefold())
 return {"workspace_label":"Configured workspace","scanned_root":folder.relative_to(base).as_posix() or ".","files":found,"total_files":len(found),"truncated":truncated,"skipped":skipped,"message":"Read-only scan complete. No files were changed."}
