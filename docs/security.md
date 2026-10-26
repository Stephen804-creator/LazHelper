# Security notes
- Configure LAZHELPER_ALLOWED_ROOT to the specific folder you want to inspect; avoid drive roots and entire home directories.
- Run on loopback only. Do not expose this prototype to the internet.
- File content is untrusted input; prompt injection cannot be eliminated completely. Review recommendations.
- Extracted content is returned to the browser and sent to the configured Ollama endpoint when AI is requested.
- The app does not log document text.
- Parser vulnerabilities remain possible; keep dependencies updated and inspect untrusted files cautiously.
- The hosted workspace's scanning and analysis routes remain separate from local device operations.
- The optional Laz Connector can perform local file changes only within explicit grants and after the approval policy is satisfied. Its delete action moves an individual file to quarantine; it does not permanently erase it.
- See local-connector-architecture.md for connector pairing, grants, protected locations, and activity logging.
