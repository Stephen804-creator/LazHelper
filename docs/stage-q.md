# Stage Q — Assistant profiles and personal memory

## Profiles

Choose General, Study, Research, Personal Organiser, Developer, or Custom. Profiles provide bounded guidance for the existing local Gemma recommendation prompt. The deterministic API continues to enforce path boundaries, permissions, and explicit approval requirements.

Selecting a profile does not enable file creation, editing, moving, deletion, or command execution.

## Personal memory

Saved global, folder-specific, and task-specific instructions already live in the local SQLite policy database. This stage adds an explicit **Use saved instructions** toggle, disabled by default. When enabled, applicable instructions are added to the local Gemma recommendation context with a clear statement that they are guidance only and cannot override safety rules or grant permissions. Folder rules match the selected file's workspace-relative path; task rules match the analysis task type.

Instructions are bounded and limited to 50 rules. They are not exported to external providers by this stage. This is simple owner-managed preference memory, not automatic collection of conversation history.

## API

- `GET /api/assistant-profile`
- `PUT /api/assistant-profile` with `profile` and/or `memory_enabled`
- Existing `GET/PUT /api/instructions` endpoints manage the saved rules.

The default model remains the configured local Ollama Gemma model (default `gemma3:1b`). No model-provider management or cloud AI dependency is added.
