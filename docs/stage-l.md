# LazHelper Stage L — Portable organisation plans

Stage L makes review-first organisation plans portable between machines and workspace sessions.

## Export

- `POST /api/plans/export`
- Request: `{"relative_paths":["notes.txt","Assignments/lab.pdf"],"export_format":"json"}`
- Set `export_format` to `csv` for CSV output.

Exports include a versioned schema, generated timestamp, source and destination paths, plan status and explanation, confidence score, and source-file metadata (size, modification time in nanoseconds, and SHA-256 for files up to 32 MiB). Export is a preview and does not move files.

## Import and validation

- `POST /api/plans/import`
- Request: `{"content":"<file contents>","import_format":"json"}`
- `import_format` accepts `json` or `csv`; content is limited to 2 MB and 500 items.

The importer rejects unknown JSON schema versions, validates source files and relative destinations against the current configured workspace, checks symbolic links, compares source metadata to detect changed files, and rechecks destination collisions. Items are marked `ready`, `stale`, `conflict`, or `already_organised`. Invalid rows are returned in an error list instead of being silently accepted.

## Safety contract

Import is strictly preview-only: `files_changed=false`, `apply_allowed=false`, and every imported item has `approved=false`. Stage L never calls the apply operation. A plan must be reviewed in the current workspace, and each move must still pass the existing `POST /api/organize/apply` per-item explicit-approval flow. Paths are never trusted simply because they appeared in an exported file. Destination collisions are never overwritten.

## Tests

`tests/test_stage_l.py` covers JSON/CSV round trips, file metadata, stale-source detection, collision detection, unsafe paths, invalid schemas, and read-only import behavior.
