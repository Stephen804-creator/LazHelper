# Security notes
- Configure LAZYHELPER_ALLOWED_ROOT to the specific folder you want to inspect; avoid drive roots and entire home directories.
- Run on loopback only. Do not expose this prototype to the internet.
- File content is untrusted input; prompt injection cannot be eliminated completely. Review recommendations.
- Extracted content is returned to the browser and sent to the configured Ollama endpoint when AI is requested.
- The app does not log document text.
- Parser vulnerabilities remain possible; keep dependencies updated and inspect untrusted files cautiously.
- Units 1–5 never mutate user files.
