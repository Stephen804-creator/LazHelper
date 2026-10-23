# LazHelper Stages F–K

Stages F–K extend the existing Stages A–E workspace intelligence features. They add recovery visibility, project profiles, safe ZIP inspection, natural-language command previews, local evidence retrieval, and reusable read-only workflows.

## Stage F — Recovery visibility and journal export

- `GET /api/recovery/history?limit=100&export_format=json`
- `GET /api/recovery/history?limit=100&export_format=csv`
- `GET /api/recovery/inspect/{operation_id}`

History exports contain existing operation-journal records. The inspection endpoint checks current source/destination presence and reports whether an operation appears eligible for undo. It is advisory: the existing undo operation revalidates paths and collisions before changing files. The export is returned as JSON data; the browser interface downloads a local JSON or CSV file.

## Stage G — Project and study workspace profiles

- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `GET /api/projects/{project_id}/overview`
- `PUT /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`

Profiles store a name, type, description, folder path, tags, and suggested folder names in a separate local SQLite database. The overview summarizes the selected folder. Suggested structure is metadata only: it is not created automatically. Deleting a profile deletes only the profile record, never project files.

Example creation body:

```json
{
  "name": "Cloud Computing",
  "kind": "study",
  "description": "Course notes and practicals",
  "folder_path": ".",
  "tags": ["cloud", "networking"],
  "structure": ["Lecture Notes", "Assignments", "Research", "Presentations"]
}
```

## Stage H — Safe ZIP archive inspection

- `POST /api/archive/inspect`

Example body: `{"relative_path":"downloads/course.zip","max_entries":500,"preview_text":false}`.

Inspection is inventory-only. It checks for absolute and parent-traversal paths, symbolic links, encrypted entries, oversized members, cumulative expanded-size limits, excessive compression ratios, and entry-count limits. Optional text previews are limited to allowlisted text formats and small members. No extraction occurs. A ZIP file is still untrusted input; review warnings and keep the application private to the local machine.

## Stage I — Natural-language command previews

- `POST /api/commands/preview`

Example body: `{"command":"find cloud computing notes","relative_path":"."}`.

The parser maps a small, explicit set of phrases to supported intents such as search, duplicates, related files, workspace health, knowledge map, archive inspection, or project workspace tools. It returns a proposed action and parameters. It does not run shell commands, delete files, or execute arbitrary instructions. Unknown or destructive requests are reported as unsupported.

## Stage J — Local document evidence retrieval

- `POST /api/knowledge/ask`

Example body: `{"question":"What services are common in cloud computing?","relative_path":".","max_sources":5}`.

This version searches supported, readable local files and ranks matching sentences by token overlap. Results include source paths and evidence passages. It is deliberately described as evidence retrieval, not as a complete generated answer. No document content is sent to a model or external service. OCR and semantic embeddings are not included in this stage.

## Stage K — Reusable read-only workflows

- `GET /api/workflows`
- `POST /api/workflows`
- `GET /api/workflows/{workflow_id}`
- `POST /api/workflows/{workflow_id}/run`
- `DELETE /api/workflows/{workflow_id}`

Workflows may contain up to 10 steps from a fixed allowlist: `search`, `relationships`, `duplicates`, `health_report`, and `knowledge_map`. Parameters are validated when a workflow is saved. A run executes the saved analyses and returns their results. It never moves, renames, overwrites, extracts, or deletes files. Deleting a workflow removes only workflow metadata.

## Storage and safety

- Project profiles and workflows are stored in `.lazhelper_extended.sqlite3` under the project directory. They contain local metadata and should be treated as private to the machine/user running the application.
- Existing operation-journal data remains in the organizer's existing database.
- Paths are resolved through the existing workspace-confined scanner; parent traversal and symlinks are rejected.
- Workflows are read-only and allowlisted. Natural-language requests are parsed as suggestions, not treated as executable code.
- Archive inspection is bounded and never extracts files.
- The application does not add authentication. Keep the server bound to loopback; do not expose it directly to the public internet.
- Run `python -m pytest -q` and verify the GitHub Actions check before considering this development branch release-ready.
