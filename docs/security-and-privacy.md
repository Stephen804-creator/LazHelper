# Security and Privacy

Laz Helper is designed to make file understanding and organization transparent, with clear workspace boundaries and user-reviewed changes.

## Workspace boundaries

- Configure the workspace folder that Laz Helper should inspect.
- Scanning follows the configured workspace boundary and does not follow symbolic links.
- Scan depth, file counts, file size, extracted text, and format-specific processing are bounded.
- Scanning and extraction leave file contents and locations unchanged.
- Source files are treated as text, and ZIP archives are inventoried without extracting their contents.

## AI and document handling

- AI-assisted recommendations use the configured Ollama endpoint.
- The application sends extracted document content to that endpoint when an AI recommendation is requested.
- Workspace insights summarize file metadata such as counts, extensions, folder distribution, and file sizes.
- AI recommendations are presented for review before users decide how to organize files.

## File-change control

- Organization plans preview proposed destinations before changes are applied.
- Users explicitly approve file moves.
- Existing destination files are not silently overwritten.
- Duplicate discovery reports exact matches without deleting files.
- Sloth Mode prepares scheduled review summaries rather than moving or deleting files automatically.
- The operation journal records supported moves and provides an undo path when the original location is available.

## Local data

Laz Helper stores preferences, operation history, and workspace data using the configured local filesystem and SQLite state. The selected workspace and AI endpoint determine how files are processed and where AI requests are sent.
