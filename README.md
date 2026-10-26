# Laz Helper

**Understand your files. Organise your workspace with confidence.**

Laz Helper is a local-first file-understanding assistant that helps you inspect a workspace, understand supported documents, and organise files through reviewable recommendations. It combines bounded file scanning, content extraction, optional AI assistance, and safeguards that keep file-changing actions under your control.

Its workflow is simple: **Scan → Understand → Recommend → Review → Organise**.

## Features

### File scanning and document understanding
- Scan a configured workspace with limits on traversal depth, file count, and file size.
- Extract text and metadata from supported formats, including PDF, DOCX, TXT, Markdown, RTF, CSV, XLS/XLSX, and PPTX.
- Inspect common image formats through metadata and list ZIP archive contents without extracting them.
- Inspect source and structured-text files as text; scanned code is not executed.
- Continue using scanning and supported extraction without an AI service.

### AI-assisted recommendations
- Optionally use an Ollama model to generate structured file descriptions, summaries, and organisation suggestions.
- Sanitize proposed filenames and categories before presenting recommendations.
- Treat AI output as advisory: users review suggestions before applying file changes.

### Review-first file organisation
- Preview proposed destinations using configurable file-category rules.
- Require explicit approval before moving files.
- Refuse destination collisions rather than silently overwriting existing files.
- Identify exact duplicates using file hashes.
- Place uncertain files in a review queue instead of forcing a category.
- Record supported file operations and provide undo when the original location is available.

### Workspace preferences and scheduled review
- Configure category rules and organisation preferences for a workspace.
- Use optional **Sloth Mode** to review a chosen inbox on a schedule.
- See which files are ready for review, need attention, or have destination conflicts. Scheduled reviews prepare summaries and do not move or delete files automatically.

### Workspace insights
- Summarise file counts, file extensions, folder distribution, total size, and largest files.
- Generate these insights from file metadata without sending file contents to an AI provider.

## Safety and privacy

Laz Helper is designed around workspace boundaries and review before action.

- Scanning is restricted to the configured workspace root, and symbolic links are not followed.
- Scan depth, file counts, file size, and extracted text are bounded.
- Scanning and extraction do not change files.
- File moves require an explicit approval step; destination collisions are refused.
- Duplicate detection reports matches rather than deleting files.
- ZIP files are inventoried rather than extracted, and source code is treated as text rather than executed.
- Image handling provides metadata; OCR is not part of the current scanning workflow.
- If AI recommendations are enabled, the extracted content used for a recommendation is sent to the configured Ollama service. Review the service configuration before processing sensitive documents.

**Laz Helper does not provide user authentication.** Run it locally; do not expose it directly to the public internet or process sensitive workspace data through an unauthenticated deployment.

## Documentation

- [Product overview](docs/product-overview.md)
- [Architecture](docs/architecture.md)
- [File organization](docs/file-organization.md)
- [Scheduled reviews and workspace insights](docs/scheduled-reviews-and-insights.md)
- [Security and privacy](docs/security-and-privacy.md)

## Technology

- Python 3.11+
- FastAPI
- Pydantic
- Ollama (optional AI recommendations)
- Pytest

The repository licence and the selected AI model's licence are separate. Check the model's own usage terms and hardware requirements.

## Run locally

Requirements: Python 3.11 or later and Git. Ollama is optional.

Clone the repository and enter the project directory:

```bash
git clone https://github.com/Stephen804-creator/LazHelper.git
cd LazHelper
python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, review the workspace and AI settings, then start the application:

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser. Keep the development server local.

## Optional AI setup

Install and start Ollama separately, then download a model compatible with your device and usage requirements. For example:

```bash
ollama pull gemma3:1b
```

Configure the selected model in your `.env` file. Laz Helper does not download models automatically. File scanning and supported content extraction remain available when Ollama is unavailable.

## Tests

Run the test suite from the project directory:

```bash
python -m pytest -q
```

Review the latest GitHub Actions result before relying on a particular commit or branch. A test suite being present does not by itself mean every test has passed.

## Contributing

Bug reports, focused improvements, documentation updates, and tests are welcome. Changes involving file operations should preserve the project's safety contract: remain inside the configured workspace, preview proposed changes, require approval for moves, refuse overwrites, and never delete user files automatically.

## Maintainer

Stephen Okeke — [GitHub](https://github.com/Stephen804-creator)
