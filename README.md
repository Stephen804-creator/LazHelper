# LazHelper 🦥

**Your files are a mess. Let AI do the boring part.**

LazHelper is being developed as **LazHelper**, a local-first file-understanding assistant. Its workflow is **Scan → Understand → Recommend → Review → Organise → Undo**.

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

Open http://127.0.0.1:8000. Sample files are in `workspace/`. To scan a different folder, set `LAZYHELPER_ALLOWED_ROOT` in your environment to that specific folder and restart the app. The API only accepts relative paths inside that configured root. Do not expose this development server to the public internet.

## Optional AI

Install Ollama separately, pull a model you are licensed and equipped to use (for example, `ollama pull gemma3:1b`), then configure `LAZYHELPER_OLLAMA_MODEL`. Model licensing is separate from this repository's MIT licence. LazHelper does not download models automatically. Scanning and extraction work when Ollama is unavailable.

## Units 6–10: review-first organisation\n\nThe `build/units-6-10` branch adds a separate organisation preview, exact SHA-256 duplicate discovery, a persistent “Not Sure” queue, a local operation journal with undo, and editable local category preferences. The preview is non-mutating; each move needs its own approval. Existing destination paths are refused, and there is no delete endpoint. Successful moves can be undone only when the original path is free. State is stored in `.lazhelper_state.sqlite3` in the project directory. See `docs/units-6-10.md` for the scope and safety contract.\n\n## Units 6–10: review-first organisation\n\nThe `build/units-6-10` branch adds an organisation preview, exact SHA-256 duplicate discovery, a persistent “Not Sure” queue, a local operation journal with undo, and editable local category preferences. Planning is non-mutating; each move needs its own approval. Existing destination paths are refused, and there is no delete endpoint. Undo is available only when the original path is free. State is stored in `.lazhelper_state.sqlite3` in the project directory. See `docs/units-6-10.md` for the scope and safety contract.\n\n## Units 11–13: Sloth Mode, insights, and recovery tests\n\nThe `build/units-11-13` branch adds opt-in Sloth Mode for scheduled inbox review, a metadata-only Digital Mess Map, and additional security/recovery tests. Sloth Mode is off by default and only prepares review summaries; it does not move files in the background. Its schedule runs only while the local app is running. Workspace insights use filenames, extensions and sizes, not document content. See `docs/units-11-13.md`.\n\n## Safety boundary

Scanning, extraction, and planning are read-only. Units 6–10 add explicit user-approved moves and undo; LazHelper never deletes files and refuses known destination collisions. It does not execute source code or extract ZIP archives. Image OCR is not enabled yet; images provide metadata only. File, page, row, text, and archive limits apply. Keep the app on loopback and review all AI recommendations.

## Tests

Run `pytest -q`. The current tests cover path traversal, workspace confinement, read-only scanning, and recommendation sanitisation.

Inbox automation and additional personalisation remain later roadmap units.
