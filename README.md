# Laz Helper

**Understand your files. Make better decisions about how to organise them.**

Laz Helper is a local-first file-understanding assistant that helps people make sense of cluttered workspaces. It scans a user-configured folder, extracts useful information from supported file formats, and prepares structured, AI-assisted recommendations so users can review what the system has learned before acting on it.

The workflow is simple: **Scan → Understand → Recommend → Review → Organise**.

## What Laz Helper does

- **Workspace scanning:** Inspects files within a configured directory, using relative paths and bounded scan limits to keep processing within a defined workspace.
- **Document understanding:** Extracts text and metadata from supported formats, including PDF, DOCX, TXT, Markdown, RTF, CSV, XLS/XLSX, PPTX, source and text files, image metadata, and ZIP inventories.
- **AI-assisted recommendations:** Uses an optional locally running Ollama model to produce structured file descriptions and organisation suggestions.
- **Human review:** Treats AI output as a recommendation, not an instruction. Generated names and categories are sanitised so suggestions can be reviewed before use.
- **Local-first operation:** File scanning and content extraction work without an AI provider. AI processing is optional.
- **Workspace boundaries:** Restricts scanning to the configured root, skips symbolic links, limits scan depth and item counts, and avoids executing source code or extracting archive contents.

Laz Helper helps users understand their files before making changes. File access and organisation actions are designed to remain explicit, reviewable, and predictable.

## How it works

1. **Choose a workspace.** Configure the directory Laz Helper is allowed to inspect.
2. **Scan and extract.** The scanner inventories files and extracts supported text or metadata within configured limits.
3. **Generate recommendations.** When local AI is configured, the application prepares structured descriptions and suggested categories.
4. **Review results.** Inspect the extracted information and recommendations before relying on them.

The scanner uses a configured workspace root and relative paths rather than accepting arbitrary filesystem paths. The application does not execute files it scans.

## Technology

- **Python 3.11 or later**
- **FastAPI** for the application and HTTP interface
- **Pydantic** for structured data validation
- **Ollama** as an optional local AI inference interface
- **Pytest** for automated tests

The application's licence and the selected AI model's licence are separate. Model availability, hardware requirements, and usage conditions depend on the model selected.

## Run locally

### Requirements

- Python 3.11+
- Git
- Optional: [Ollama](https://ollama.com/) and a compatible model for AI-assisted recommendations

### Install

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
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure the workspace and optional AI settings for your environment. Start the application:

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

Use the development server locally. Do not expose it directly to the public internet.

## Optional local AI

Laz Helper can use Ollama for local AI-assisted recommendations. Install Ollama separately, download a model that you are permitted and equipped to use, and configure the model setting in your `.env` file. For example:

```bash
ollama pull gemma3:1b
```

The model is not downloaded automatically. File scanning and extraction remain available when Ollama is not running.

## Safety and privacy

Laz Helper is built around workspace boundaries and review before action.

- Scanning is limited to the configured workspace root.
- Symbolic links are skipped.
- Scan depth, file counts, and extracted content are bounded.
- File scanning and extraction are read-only.
- AI-generated recommendations are suggestions for the user to review.
- Source code is not executed, and ZIP files are inventoried rather than extracted.
- Image handling provides metadata; OCR is not part of the current scanning workflow.

Use the application only with directories you are authorised to access, and review the configuration before processing sensitive files.

## Tests

Run the automated test suite from the repository root:

```bash
pytest -q
```

The tests cover core safety behaviour, including workspace confinement, path traversal protection, read-only scanning, and recommendation sanitisation.

## Contributing

Contributions that improve file understanding, safety, accessibility, reliability, testing, and documentation are welcome. For substantial changes, open an issue to discuss the proposal and include relevant tests with code changes.

## Licence

The repository licence is defined in the [LICENSE](LICENSE) file. AI models used with Laz Helper may have separate licences and usage conditions.

## Maintainer

Created and maintained by [Stephen Okeke](https://github.com/Stephen804-creator).
