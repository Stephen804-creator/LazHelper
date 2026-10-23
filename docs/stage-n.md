# Stage N — Unified Ask LazHelper and voice

Stage N gives the user one entry point for questions and task requests. The user chooses either **Ask my local documents** or **Preview a task**. Questions use the existing local evidence-retrieval endpoint; task requests use the existing allowlisted natural-language parser and return a preview only. The chat does not execute file operations.

Voice input uses the browser's Web Speech API when supported. It fills the same text field and lets the user review the transcript before submitting it, so voice and text follow the same backend policies. Unsupported browsers retain the full text interface. Optional read-aloud uses browser speech synthesis.

The UI shows actual request status, safely renders responses as text, and presents local evidence paths. It does not claim that extractive evidence retrieval is a generated Gemma answer. The existing optional local Gemma/Ollama adapter remains the AI recommendation core; Stage N does not add another model provider or make cloud requests.
