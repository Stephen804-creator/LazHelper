# Unit 1 — Architecture
## Components
- Browser UI: static HTML/CSS/JavaScript; same-origin JSON APIs; file names rendered as text nodes.
- FastAPI: request validation, API errors, and UI hosting.
- Workspace boundary: configured root, relative paths, canonical checks, symlinks rejected.
- Scanner: bounded metadata inventory; no writes.
- Extractors: bounded parsers; code is text only; ZIP is inventoried without extraction.
- AI adapter: optional Ollama client with Pydantic validation and filename/category sanitisation.
## Data flow
1. User requests a workspace scan.
2. Scanner returns file metadata.
3. User selects a file.
4. Backend validates path and extracts bounded content.
5. Optional local AI returns structured recommendations.
6. UI displays results; nothing is applied.
## Security
File size, scan count, depth, text, pages, rows, slides, and archive entries are bounded. No wildcard CORS. No telemetry or remote AI provider is configured. Keep this prototype on loopback; it is not hardened for public multi-user hosting.
