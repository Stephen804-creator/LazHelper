# Stage M — Owner permissions and instruction policies

LazHelper keeps its existing local workspace and Gemma/Ollama setup. This stage adds owner-controlled capabilities without adding a model-provider management system.

## Permissions

Read-only scanning and content understanding remain available by default. File-changing capabilities are opt-in and default to off: create files/folders, edit, rename, move, copy, export, restore/undo, delete, and run commands. The interface lists these capabilities and saves the settings through `PUT /api/permissions`; the policy is persisted in the local SQLite state database.

The API checks permissions centrally, so hiding or bypassing the UI does not bypass the policy. File moves still require per-item `approved: true`; permission to move is not itself approval. Undo requires its own permission. Delete and command execution remain disabled and no new delete/command endpoint is introduced.

## Scope and instructions

Permissions are constrained to the configured workspace. The owner may store up to 50 bounded global, folder-specific, or task-type instructions. Instructions affect recommendations only; they never grant capabilities, authorize a file change, or override application safety rules.

## Local-first AI

The existing Ollama adapter remains the model integration and the configured default is `gemma3:1b`. Gemma provides recommendations; deterministic application code enforces permissions and workspace boundaries. The app continues to work for basic scanning and extraction when Ollama is unavailable.

## Verification

`tests/test_stage_m_policies.py` covers default-off write capabilities, explicit enablement, policy validation, instruction scope validation, and the separation between instructions and permissions.
