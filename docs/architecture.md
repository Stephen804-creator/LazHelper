# Architecture

Laz Helper is a local-first web application with a browser interface, a FastAPI backend, bounded file-processing components, and optional local AI recommendations.

## Components

- **Browser interface:** HTML, CSS, and JavaScript served by FastAPI. The interface communicates with same-origin JSON endpoints.
- **API layer:** FastAPI routes validate requests, return structured results, and translate expected errors into HTTP responses.
- **Workspace boundary:** Configuration defines the allowed root. Paths are resolved and checked before supported file operations; symbolic links are not followed during scanning.
- **Scanner:** Builds a bounded inventory of files and metadata without modifying the workspace.
- **Extractors:** Read supported documents using bounded processing limits. Source code is treated as text, and ZIP archives are inventoried without extracting their contents.
- **AI adapter:** Optionally sends extracted content to the configured Ollama service and validates the returned recommendation.
- **Organizer:** Builds proposed destinations, identifies exact duplicates, manages the review queue and preferences, and records approved moves for undo.
- **Scheduled review and insights:** Sloth Mode prepares inbox reports while the process is running; workspace insights summarize metadata.
- **Local state:** SQLite stores supported operation history, preferences, queue information, and scheduled-review settings.

## Main request flows

### Inspecting a workspace

1. The browser requests a scan of a relative path.
2. The scanner checks the path against the configured workspace and returns a bounded file inventory.
3. The user selects a supported file.
4. The backend extracts bounded text or metadata.
5. If AI recommendations are available and requested by the analysis flow, the configured Ollama service returns advisory information.
6. The browser displays the extracted information and recommendation for human review.

### Organizing files

1. The user requests an organization preview.
2. The organizer applies configured category rules and identifies uncertain items or destination conflicts.
3. The interface presents the proposed changes.
4. The user explicitly approves eligible moves.
5. Successful moves are recorded in the local operation journal; undo is available when the original path is free.

## Processing boundaries

File count, scan depth, file size, extracted text, and format-specific extraction limits are bounded. Scanning and extraction do not change files. Recommendations do not initiate file operations. Destination collisions are refused, and duplicate detection does not delete files.

## Deployment considerations

The current application does not implement authentication or authorization. Run it locally and do not expose it directly to the public internet. SQLite state and workspace files are local to the configured filesystem; on hosting platforms with ephemeral storage, they may not persist across restarts or redeployments.
