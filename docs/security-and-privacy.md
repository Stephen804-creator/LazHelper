# Security and Privacy

Laz Helper protects a configured workspace and requires explicit approval before moving files. Its guarantees apply to the backend host's configured workspace; a hosted deployment does not gain access to files on a visitor's phone or computer.

## API access

- All `/api/*` routes except `/api/health` require a bearer token.
- Configure `LAZ_HELPER_API_TOKEN` with a random value of at least 32 characters.
- The Render blueprint generates a token. Retrieve it from the Render service environment settings and enter it in the browser unlock screen.
- The browser keeps the token in session storage for the current tab session and sends it in the Authorization header. The Lock action clears the token, in-memory workspace state, and rendered document details from the page.
- Workspace API responses use `Cache-Control: no-store`; the application also sets a restrictive Content Security Policy and baseline browser security headers.
- Do not share the token or expose it in source control, URLs, screenshots, or logs. Use HTTPS for remote access.

## Workspace boundaries

- Configure the workspace folder that the backend is allowed to inspect.
- API paths must be relative and cannot contain parent-directory traversal, drive prefixes, or backslash path separators.
- POSIX file opens walk directory descriptors and refuse symbolic links; file reads use no-follow handles.
- On platforms without POSIX directory-descriptor support, path resolution and before/after inode checks are used as a compatibility fallback; the POSIX path has stronger race resistance.
- Scanning does not follow symbolic links and is bounded by scan depth, file count, and file size.
- Extraction is bounded by file size, text length, page/slide/sheet previews, image dimensions, and archive entry/expansion limits.
- Scanning and extraction do not change file contents or locations.
- Source files are treated as text, and ZIP archives are inventoried without extracting their contents.

## AI and document handling

- AI-assisted recommendations use the configured `LAZ_HELPER_OLLAMA_URL` and model.
- When an AI recommendation is requested, extracted document content is sent to that endpoint. If it points to a local Ollama service, content is processed locally. If it points to a remote service, document content is transmitted to that remote endpoint and its operator may process or retain it under their own policies.
- Workspace insights summarize metadata such as counts, extensions, folder distribution, and file sizes; they do not send document contents to the AI endpoint.
- AI output is untrusted advice. It cannot initiate file operations, and recommendations remain subject to human review.

## File-change control

- Organization plans preview proposed destinations before changes are applied.
- Every move requires explicit approval.
- Destination files are created exclusively; existing destination files are not overwritten.
- Source reads and move operations use symlink-resistant file handles on POSIX systems. Undo also refuses to overwrite an existing original path.
- Duplicate discovery hashes files and reports exact matches without deleting them.
- Sloth Mode is opt-in and prepares review summaries; it does not move or delete files.
- The operation journal records supported moves and provides an undo path when the original location is available. It is not a backup system.

## State and hosting

- Preferences, review queue entries, and operation history use SQLite by default.
- When `DATABASE_URL` is configured, application state uses PostgreSQL. Workspace files remain on the backend host's filesystem.
- A hosted web service does not inspect a visitor's local filesystem. The Render service filesystem is ephemeral unless persistent storage is configured; do not store important personal files in an ephemeral deployment workspace.
- Sloth Mode runs inside each application process. Avoid enabling it on multi-instance deployments unless a single scheduler/leader is configured.
- Use a trusted Ollama endpoint, keep dependencies updated, and back up both the workspace and application database before important operations.
