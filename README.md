# Laz Helper

**Understand your files. Organise your workspace with confidence.**

Laz Helper helps you make sense of busy folders, understand documents, and organise files with less manual effort. Its review-first workflow brings file scanning, document understanding, AI-assisted recommendations, duplicate discovery, and workspace insights together in one straightforward interface.

**Workspace boundary:** Laz Helper can only inspect files in the folder configured on the machine or server running the backend. Running it locally gives it access to your configured local folder. A Render deployment accesses the server's workspace, not files on your phone or computer.

**Scan → Understand → Review → Organise**

## What you can do

### Understand your files
- Scan a workspace with configurable limits for depth, file count, and file size.
- Extract text and metadata from PDF, DOCX, TXT, Markdown, RTF, CSV, XLS/XLSX, and PPTX files.
- Inspect common image metadata and view ZIP archive contents without extracting them.
- Review source and structured-text files without executing them.

### Get AI-assisted recommendations
- Use an Ollama-compatible model to generate file descriptions, summaries, and organization suggestions.
- Extracted document content is sent to the configured `LAZ_HELPER_OLLAMA_URL` when an AI recommendation is requested. This may be a local or remote endpoint.
- Review recommendations and proposed names before applying file changes.
- Keep document processing and organization decisions transparent and under your control.

### Organise with confidence
- Preview proposed destinations using configurable file-category rules.
- Approve file moves explicitly.
- Identify exact duplicates using file hashes.
- Send uncertain files to a review queue.
- Review operation history and undo supported moves when the original location is available.

### Keep your workspace in view
- Configure organization rules and preferences.
- Use Sloth Mode to prepare scheduled inbox-review summaries.
- See file counts, extension and folder distributions, total size, and largest files.
- Review summaries before deciding what needs attention.

## Built around user control

Laz Helper keeps scanning and file changes separate. Scanning and extraction leave files in place; organization plans are presented for review; approved moves are recorded; and duplicate discovery reports matches rather than deleting files. Workspace insights use file metadata to summarize a collection.

## Documentation

The [documentation index](docs/README.md) provides guides to the product, architecture, file organization, scheduled reviews, and privacy.

- [Product overview](docs/product-overview.md)
- [Architecture](docs/architecture.md)
- [File organization](docs/file-organization.md)
- [Scheduled reviews and workspace insights](docs/scheduled-reviews-and-insights.md)
- [Security and privacy](docs/security-and-privacy.md)

## Technology

- Python 3.11+
- FastAPI and Pydantic
- Ollama-compatible AI models
- SQLite for local development and PostgreSQL for deployments configured with `DATABASE_URL`
- Bearer-token protection for workspace API routes
- Pytest for automated tests

Laz Helper's AI integration is designed to work with Ollama-compatible models, including open-weight models such as Gemma. Choose a model that suits your device and intended workload.

## Get started

Requirements: Python 3.11 or later and Git.

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/Stephen804-creator/LazHelper.git
cd LazHelper
python -m venv .venv
```

Activate the environment.

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set `LAZ_HELPER_API_TOKEN` to a random value of at least 32 characters, review the workspace settings, and start Laz Helper:

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 in your browser and enter the access token when prompted. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## AI-assisted recommendations

Laz Helper sends extracted content to the configured Ollama-compatible endpoint for AI-assisted file descriptions, summaries, and organization suggestions. When the endpoint is local, content is processed by your local Ollama service. If you configure a remote endpoint, the extracted content leaves the machine running Laz Helper and is sent to that remote service. Install and start Ollama locally, then download a model suited to your device. For example:

```bash
ollama pull gemma3:1b
```

Set the model and Ollama endpoint in your `.env` configuration. For local development, Laz Helper stores preferences and operation history in SQLite. When `DATABASE_URL` is configured, it uses PostgreSQL for shared application state. Workspace files themselves remain on the filesystem of the backend host.

The Render blueprint generates `LAZ_HELPER_API_TOKEN`; retrieve it from the service environment settings and enter it in the browser unlock screen. Keep it private and use HTTPS. The blueprint's default Ollama URL points to loopback inside the Render container, not to Ollama running on your computer. Configure `LAZ_HELPER_OLLAMA_URL` to a reachable Ollama-compatible endpoint if hosted AI recommendations are required; extracted file content will be sent to that endpoint.

Render's ordinary service filesystem is ephemeral unless persistent storage is separately configured, so do not treat a free Render workspace as durable storage for important personal files. Run Laz Helper locally when you need it to work directly with files on your own computer.

## Run tests

```bash
python -m pytest -q
```

## Contributing

Bug reports, focused improvements, documentation updates, and tests are welcome. Contributions to file organization should preserve the review-first workflow and keep file-changing actions under the user's control.

## Maintainer

Stephen Okeke — [GitHub](https://github.com/Stephen804-creator)
