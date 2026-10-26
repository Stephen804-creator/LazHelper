# Security and Privacy

Laz Helper is designed for local use and keeps file-changing actions under explicit user control. Review the following boundaries before processing sensitive files or configuring a deployment.

## Workspace access

- Configure the allowed root to a specific folder intended for review; avoid selecting an entire drive or home directory without a clear need.
- File operations are intended to remain within the configured workspace.
- Scan depth, file counts, file size, extracted text, and format-specific processing are bounded.
- Scanning and extraction do not change file contents or locations.
- Source files are treated as text, not executed. ZIP archives are inventoried rather than extracted.

## AI and document privacy

- AI recommendations are optional and use the configured Ollama endpoint.
- When AI analysis is requested, extracted document content used for the recommendation is sent to that configured service. Confirm where the service runs and who can access it before analyzing sensitive material.
- Workspace insights use file metadata and do not send document contents to an AI provider.
- Treat extracted document content and AI output as untrusted. Review suggestions before using them.

## File changes and recovery

- Organization plans are previews; file moves require explicit approval.
- Existing destination files are not silently overwritten.
- Duplicate detection reports exact matches and does not delete files.
- Sloth Mode creates review summaries and does not move or delete files in the background.
- Undo can restore a recorded move only when the original location is available. It is not a substitute for backups.

## Deployment

Authentication and authorization are not implemented in the current application. Keep Laz Helper on loopback for local use and do not expose it directly to the public internet or operate it as a public multi-user service.

The operation journal, preferences, scheduled-review settings, and workspace contents rely on local storage. Hosting platforms with ephemeral filesystems may lose these records or files during restarts and redeployments.
