# LazHelper 🦥

**A calmer way to understand, organise, and recover your digital workspace.**

LazHelper is a local-first, open-source file-understanding assistant being developed in the `LazHelper` repository. It helps you inspect files, understand their formats and contents, prepare organisation suggestions, review uncertain items, find exact duplicates, and undo supported moves.

Its guiding workflow is:

**Scan → Understand → Recommend → Review → Organise → Undo**

LazHelper is designed to keep the user in control. Recommendations and plans are previews—not permission to change files.

## Current capabilities

### Inspect and understand files
- Scan a configured workspace with limits on scan depth, file count, and file size.
- Extract content or metadata from supported formats, including PDF, DOCX, TXT, Markdown, RTF, CSV, XLS, XLSX, PPTX, common image formats, source code, structured text, and ZIP inventories.
- Generate optional local AI recommendations through Ollama.
- Continue scanning and extracting when Ollama is unavailable.

### Organise with review and recovery
- Preview proposed destinations using configurable file-category rules.
- Require explicit approval for each move.
- Refuse destination collisions rather than silently overwrite files.
- Detect exact, byte-for-byte duplicates using SHA-256.
- Place uncertain files in a persistent **Not Sure** review queue.
- Keep a local operation journal and support undo when the original path is available.
- Store personal category preferences locally.

### Workspace intelligence (Stages A–E)
- Find explainable candidate relationships between files using shared filename terms, folder context, and likely version suffixes.
- Combine exact SHA-256 duplicate detection with cautious filename-version families and bounded text-similarity hints.
- Search filenames and supported extracted content locally, with short evidence snippets.
- Build a lightweight knowledge graph of folder/file nodes and candidate relationship edges.
- Generate a workspace health checklist for generic names, large or unsupported files, old files, crowded folders, and repeated naming patterns.
- Keep all suggestions read-only: no automatic renaming, merging, moving, or deletion. Content search and similarity inspection stay local and do not send data to an AI provider.

### Recovery, projects, and local workflows (Stages F–K)
- Export the operation journal as JSON or CSV and inspect whether a past move appears currently eligible for safe undo.
- Save study, research, work, or development workspace profiles with tags and suggested folder structures; metadata is stored without creating folders.
- Inspect ZIP archive contents with path, symlink, encryption, member-size, entry-count, expanded-size, and compression-ratio checks. Archive inspection never extracts files.
- Translate supported natural-language requests into reviewable action proposals; unsupported and destructive commands are not executed.
- Retrieve relevant evidence passages from local documents with source paths. This is local retrieval, not an unsupported claim of a complete AI-generated answer.
- Save and run reusable, allowlisted read-only workflows for search, relationships, duplicate/version checks, workspace health, and knowledge maps.
- Keep file-changing actions outside these stages; existing move operations still require explicit approval.

### Sloth Mode and workspace insights
- Enable **Sloth Mode** to review a chosen inbox on a configurable schedule.
- See a summary of files ready for review, uncertain items, and conflicts.
- Keep Sloth Mode disabled by default; scheduled reviews do not move or delete files.
- View metadata-only workspace insights: file counts, extensions, folder summaries, total size, and largest files.

## Project status

This development line contains Units 1–13 plus workspace-intelligence Stages A–K:

| Unit | Focus |
| --- | --- |
| 1 | Product specification and architecture |
| 2 | FastAPI foundation and responsive dashboard |
| 3 | Bounded, workspace-confined file scanner |
| 4 | File content extraction and format understanding |
| 5 | Optional local AI integration |
| 6 | Review-first organisation plans |
| 7 | Exact duplicate discovery |
| 8 | Not Sure review queue |
| 9 | Operation journal and undo |
| 10 | Local preferences and category rules |
| 11 | Opt-in Sloth Mode |
| 12 | Digital Workspace Insights |
| 13 | Testing, security, and recovery work |
| A | Intelligent file relationships |
| B | Duplicate and version insights |
| C | Unified content-aware search |
| D | Workspace knowledge map |
| E | Workspace health reports |
| F | Recovery visibility and journal export |
| G | Project and study workspace profiles |
| H | Safe ZIP archive inspection |
| I | Natural-language command previews |
| J | Local document evidence retrieval |
| K | Reusable read-only workflows |

These features are under development. Check the linked pull requests and their CI results before treating the development line as release-ready. Stages F–K do not automatically create folders, extract archives, execute shell commands, or mutate files. Unit 14, final packaging and release handoff, is not represented as complete here.

## Requirements

- Python 3.11 or newer
- A supported operating system for Python and the required packages
- Ollama only if you want local AI recommendations

## Run locally

Clone the repository and enter its directory:

```bash
git clone https://github.com/Stephen804-creator/LazHelper.git
cd LazHelper
```

Create and activate a virtual environment.

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust the settings if needed. Then start the app:

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** in your browser. API documentation is available at **http://127.0.0.1:8000/docs** while the server is running. Sample workspace files are provided in `workspace/`.

To work with a different folder, set `LAZHELPER_ALLOWED_ROOT` to that folder in `.env` and restart the application. Use a folder you are comfortable allowing LazHelper to inspect and, only after approval, organise.

## Configuration

The main environment settings are:

| Variable | Purpose | Default |
| --- | --- | --- |
| `LAZHELPER_ALLOWED_ROOT` | Workspace LazHelper is allowed to access | `./workspace` |
| `LAZHELPER_MAX_FILES` | Maximum number of files in a scan | `1500` |
| `LAZHELPER_MAX_DEPTH` | Maximum directory traversal depth | `8` |
| `LAZHELPER_MAX_FILE_MB` | Maximum file size in MB for supported processing | `20` |
| `LAZHELPER_MAX_TEXT_CHARS` | Maximum extracted text passed through the processing pipeline | `18000` |
| `LAZHELPER_OLLAMA_URL` | Local Ollama service URL | `http://127.0.0.1:11434` |
| `LAZHELPER_OLLAMA_MODEL` | Ollama model name | `gemma3:1b` |
| `LAZHELPER_AI_TIMEOUT_SECONDS` | AI request timeout | `45` |

Limits are bounded by the application. Values above the supported maximum are capped.

## Optional local AI with Ollama

AI recommendations are optional. Install and start Ollama separately, then pull a model supported by your device and whose licence suits your use. For example:

```bash
ollama pull gemma3:1b
```

Set `LAZHELPER_OLLAMA_MODEL` in `.env` to the model you installed. LazHelper does not automatically download models. Model requirements and licences are separate from the licence for this repository. Without a working Ollama service, file scanning and supported content extraction can still be used.

## Safety and privacy

LazHelper is designed around local processing and explicit user control, but it is still development software.

- **Workspace boundary:** file paths must remain inside the configured workspace; symlinks are skipped or rejected.
- **Review before action:** organisation plans do not change files. Moves require explicit approval.
- **No automatic deletion:** duplicate discovery reports matches; it does not remove them.
- **No silent overwrite:** known or newly appearing destination collisions are refused.
- **Undo has conditions:** a move can be undone only if the original path is still available.
- **Sloth Mode is review-only:** scheduled runs prepare summaries; they do not apply moves.
- **Metadata-only insights:** workspace insights use file paths/names, extensions, and sizes rather than uploading file contents.
- **Local AI:** when enabled, extracted content used for a recommendation is sent to the configured Ollama service. Review what you process and configure the service appropriately.
- **Processing limits:** size, depth, text, and file-count limits help constrain resource use.
- **No public deployment by default:** the app does not provide authentication. Keep it bound to loopback and do not expose the development server directly to the internet.

Image OCR is not currently enabled; images are represented by metadata. ZIP files are inventoried rather than extracted, and source files are treated as text rather than executed.

## Tests

Install the project dependencies, then run:

```bash
python -m pytest -q
```

The suite includes tests for scanning and path confinement, organisation safeguards, Sloth Mode behaviour, workspace insights, and recovery-related cases. Check the latest GitHub Actions result for the branch or pull request you intend to use; the existence of tests does not by itself mean they have passed.

## Documentation

- `docs/units-6-10.md` — review-first organisation, duplicates, queue, journal, and preferences.
- `docs/units-11-13.md` — Sloth Mode, workspace insights, and operational boundaries.
- `docs/stages-a-e.md` — workspace relationships, duplicate/version hints, search, knowledge map, and health reports.
- `docs/stages-f-k.md` — recovery export, project profiles, ZIP inspection, command previews, local evidence retrieval, and read-only workflows.
- `docs/stages-f-k.md` — recovery export, project profiles, ZIP inspection, command previews, local evidence retrieval, and read-only workflows.
- `/docs` — interactive API documentation when the local server is running.

## Contributing

Issues, bug reports, test improvements, and focused pull requests are welcome. For changes that touch file operations, preserve the core contract: stay inside the configured workspace, show a preview, require explicit approval for moves, refuse overwrites, and never delete user files automatically.


### Portable organisation plans (Stage L)
- Export reviewable organisation plans as versioned JSON or CSV, including destination explanations, confidence scores, and source-file metadata.
- Import plans from another session or machine and validate workspace-relative paths, source freshness, and destination collisions.
- Imports are preview-only. They never move files, and each move still requires explicit approval through the existing apply flow.
- See [Stage L documentation](docs/stage-l.md).
