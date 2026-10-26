# LazHelper

**Understand your files. Make better decisions about how to organise them.**

LazHelper is a local-first file-understanding assistant that helps people make sense of cluttered workspaces. It scans a user-configured folder, extracts useful information from supported file formats, and prepares structured, AI-assisted recommendations so users can review what the system has learned before acting on it.

The goal is to make file organisation more understandable and safer: **Scan → Understand → Recommend → Review → Organise**.

## What LazHelper does

- **Workspace scanning:** Inspects files within a configured directory, using relative paths and bounded scan limits to keep processing within a defined workspace.
- **Document understanding:** Extracts text and metadata from supported formats, including PDF, DOCX, TXT, Markdown, RTF, CSV, XLS/XLSX, PPTX, source and text files, image metadata, and ZIP inventories.
- **AI-assisted recommendations:** Can use a locally running Ollama model to produce structured file descriptions and organisation suggestions.
- **Human review:** Treats AI output as a recommendation, not an instruction. The application sanitises generated names and categories so suggestions can be reviewed before they are used.
- **Local-first operation:** File scanning and content extraction can run without an AI provider. Optional AI processing is configured by the user.
- **Workspace boundaries:** Restricts scanning to the configured root, skips symbolic links, limits scan depth and item counts, and avoids executing source code or extracting archive contents.

LazHelper is designed to help users understand their files before making changes. File access and organisation actions should remain explicit, reviewable, and predictable.

## How it works

1. **Choose a workspace.** Configure the directory LazHelper is allowed to inspect.
2. **Scan and extract.** The scanner inventories files and extracts supported text or metadata within configured limits.
3. **Generate recommendations.** When local AI is configured, the application can use it to prepare structured descriptions and suggested categories.
4. **Review results.** Inspect the extracted information and recommendations before relying on them.

The scanner uses a configured workspace root and relative paths rather than accepting arbitrary filesystem paths. The application does not execute files it scans.

## Technology

- **Python 3.11 or later**
- **FastAPI** for the application and HTTP interface
- **Pydantic** for structured data validation
- **Ollama** as an optional local inference interface
- **Pytest** for automated tests

The repository's application code and an AI model have separate licensing terms. Model availability, supported hardware, and model licensing depend on the model selected by the user.

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

Copy `.env.example` to `.env` and configure the workspace settings for your environment. Start the application:

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

By default, the application should be used as a local development service. Do not expose the development server directly to the public internet.

## Optional local AI

LazHelper can use Ollama for local AI-assisted recommendations. Install Ollama separately, download a model you are permitted and equipped to use, and set the model configuration in your environment. For example:

```bash
ollama pull gemma3:1b
```

Configure `LAZYDESK_OLLAMA_MODEL` in your environment as required by the application. The model is not downloaded automatically. Scanning and extraction remain available when Ollama is not running.

## Safety and privacy

LazHelper is built around workspace boundaries and review before action.

- Scanning is limited to the configured workspace root.
- Symbolic links are skipped.
- Scan depth, file counts, and extracted content are bounded.
- File scanning and extraction are read-only.
- AI-generated recommendations must be reviewed rather than treated as commands.
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

Contributions that improve file understanding, safety, accessibility, reliability, testing, and documentation are welcome. Please open an issue to discuss a substantial change, and include relevant tests with code changes.

## License

LazHelper's repository license is defined in the [LICENSE](LICENSE) file. Any AI model used with the application may have its own separate license and usage conditions.

## Maintainer

Created and maintained by [Stephen Okeke](https://github.com/Stephen804-creator).
