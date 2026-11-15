# Architecture

Laz Helper is a workspace-scoped web application with a browser interface, FastAPI backend, bounded file-processing components, optional Ollama-compatible AI recommendations, and review-first file organization.

## Components

- **Browser interface:** HTML, CSS, and JavaScript served by FastAPI. A bearer token is required for workspace API requests; the browser keeps it in session storage for the current tab session.
- **API layer:** FastAPI routes validate requests, return structured results, and translate expected errors into HTTP responses. Only `/api/health` is public; other `/api/*` routes require `LAZ_HELPER_API_TOKEN`.
- **Workspace boundary:** Configuration defines the allowed root. Relative paths are validated, symbolic links are rejected, and POSIX file opens use directory descriptors and no-follow flags.
- **Scanner:** Builds a bounded inventory of files and metadata without modifying the workspace.
- **Extractors:** Read supported documents using bounded processing limits. Source code is treated as text, and ZIP archives are inventoried without extracting their contents. Compressed document formats are checked for excessive archive expansion before parsing.
- **AI adapter:** Sends extracted content to the configured Ollama-compatible endpoint for requested recommendations and validates the returned response. The endpoint may be local or remote.
- **Organizer:** Builds proposed destinations, identifies exact duplicates, manages the review queue and preferences, and records approved moves for undo. POSIX moves use exclusive destination creation and symlink-resistant source handles.
- **Scheduled review and insights:** Sloth Mode prepares inbox reports while the process is running; workspace insights summarize metadata only.
- **Application state:** SQLite is the default local store. When `DATABASE_URL` is configured, PostgreSQL stores operation history, preferences, and review queue state. Workspace files remain on the backend host filesystem.

## Main request flows

### Understanding a workspace

1. The browser authenticates with the configured bearer token.
2. The browser requests a scan of a relative path.
3. The scanner checks the path against the configured workspace and returns a bounded file inventory.
4. The user selects a supported file.
5. The backend opens the file through the workspace-safe file helper and extracts bounded text or metadata.
6. If requested, the configured Ollama endpoint receives the extracted content and returns an AI-assisted description or recommendation.
7. The browser displays the extracted information and recommendation for human review.

### Organizing files

1. The user requests an organization preview.
2. The organizer applies configured category rules and identifies uncertain items or destination conflicts.
3. The interface presents the proposed changes.
4. The user explicitly approves eligible moves.
5. The organizer creates the destination exclusively, copies from a no-follow source handle, removes only the expected source file, and records the move in the operation journal.
6. Undo restores the file only if the original path is still available and safe.

## Processing boundaries

File count, scan depth, file size, extracted text, archive expansion, image dimensions, and format-specific extraction limits are bounded. Scanning and extraction do not change files. Recommendations do not initiate file operations. Destination collisions are refused, and duplicate discovery does not delete files.

## Deployment boundaries

A local run can inspect files inside the local configured workspace. A hosted Render service can inspect only its server-side workspace; it cannot browse files on a visitor's device. Hosted workspace persistence depends on the hosting provider's storage configuration. Sloth Mode runs inside the application process, so multi-instance deployments need a single scheduler/leader if scheduled work is enabled.
