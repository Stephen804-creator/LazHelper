# LazyDesk 🦥

**Your files are a mess. Let AI do the boring part.**

LazHelper is being developed as **LazyDesk**, a local-first file-understanding assistant. Its workflow is **Scan → Understand → Recommend → Review → Organise → Undo**.

## Units 1–5 implemented in this branch

1. **Product specification and architecture** — scope, acceptance criteria, data flow, and security boundary.
2. **Project foundation and UI** — FastAPI app and responsive browser dashboard.
3. **Safe file scanner** — configured workspace only, relative paths, symlink skipping, bounded scan depth/count, no file modifications.
4. **Content understanding** — PDF, DOCX, TXT, Markdown, RTF, CSV, legacy XLS, XLSX, PPTX, image metadata, source/text files, and ZIP inventory.
5. **Local AI adapter** — optional Ollama integration, structured Pydantic output, filename/category sanitisation, and mandatory human review.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then run:

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Sample files are in `workspace/`. To scan a different folder, set `LAZYDESK_ALLOWED_ROOT` in your environment to that specific folder and restart the app. The API only accepts relative paths inside that configured root. Do not expose this development server to the public internet.

## Optional AI

Install Ollama separately, pull a model you are licensed and equipped to use (for example, `ollama pull gemma3:1b`), then configure `LAZYDESK_OLLAMA_MODEL`. Model licensing is separate from this repository's MIT licence. LazyDesk does not download models automatically. Scanning and extraction work when Ollama is unavailable.

## Safety boundary

Units 1–5 are intentionally read-only. LazyDesk never moves, renames, overwrites, or deletes files. It does not execute source code or extract ZIP archives. Image OCR is not enabled yet; images provide metadata only. File, page, row, text, and archive limits apply. Keep the app on loopback and review all AI recommendations.

## Tests

Run `pytest -q`. The current tests cover path traversal, workspace confinement, read-only scanning, and recommendation sanitisation.

Automatic organisation, duplicate removal, inbox automation, personalisation, and undo journal remain later roadmap units.
