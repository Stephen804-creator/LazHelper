# Laz Helper Local Connector Architecture

## Purpose

The Laz Connector is the device-side component that can access files the user explicitly grants. It is packaged from this repository but runs on the user's computer. Code deployed to Render cannot access a visitor's local filesystem.

## Components

1. **Hosted Laz Helper UI** — explains the connector, initiates pairing, requests scoped actions, and displays permission and activity status.
2. **Local connector process** — runs on `127.0.0.1:43179`; it is not exposed on the LAN or public internet.
3. **Pairing and origin checks** — a one-time code is printed by the local connector. Pairing consumes the code and returns a persistent random bearer token bound to an allowed website origin. Protected endpoints require both the expected origin and token.
4. **Permission store** — persists explicitly selected files/folders, allowed operations, scope mode, approval mode, and activity records on the device.
5. **Operation guard** — validates path containment, symlinks, protected locations, per-grant capabilities, collision handling, and approval before a mutation.
6. **OS picker** — opens a native file/folder dialog when the local desktop supports it; the browser never receives unrestricted filesystem access.

## Local API

All endpoints are under `/v1`.

- `GET /v1/health` — connector identity and version; no filesystem paths.
- `POST /v1/pair` — exchange the current one-time pairing code for a persistent token.
- `GET /v1/connection` — authenticated connection and permission summary.
- `GET /v1/permissions` — current scope, approval mode, grants, and protected-location guidance.
- `PUT /v1/permissions/preferences` — update scope/approval mode.
- `POST /v1/permissions/pick` — open a native file/folder picker and add a grant with selected capabilities.
- `DELETE /v1/permissions/grants/{grant_id}` — revoke a grant.
- `GET /v1/activity` — return recent local activity.
- `GET /v1/files` and `GET /v1/files/content` — enumerate or read files only inside a read grant; the `ask_every_time` scope requires an explicit approval flag.
- `GET /v1/duplicates` — bounded, read-only SHA-256 duplicate scan inside a read-granted folder; results never trigger deletion.
- `POST /v1/operations/preview` — validate an operation without changing a file.
- `POST /v1/operations/execute` — execute a permitted operation after approval policy checks.

## Permission model

Supported capabilities are independent: `read`, `create`, `edit`, `move`, `rename`, and `delete`. A user may grant only the capabilities they need. Folder and file grants are distinct.

Scope modes:
- `permitted_locations`: use all locations the user explicitly granted and the OS allows.
- `selected_folders`: restrict access to folder grants.
- `selected_files`: restrict access to individual file grants.
- `ask_every_time`: keep the configured grants but require a fresh explicit approval for each local file read and file-changing action.

Approval modes:
- `ask_every_time`: every mutation requires an explicit approval flag from the UI.
- `routine_auto`: create/edit can proceed without a per-operation approval only when the corresponding capability was granted; move, rename, and delete remain approval-gated.

The default is `selected_folders` plus `ask_every_time`, with no grants. No permission is inferred from a path being readable by the OS.

## Safety invariants

- The service binds to loopback only.
- File APIs require a paired bearer token and an allowlisted `Origin`.
- No path outside an explicit grant is readable or mutable.
- Symlinks are not followed.
- Common operating-system directories and filesystem roots are protected from grants.
- Existing files are never silently overwritten by create, move, or rename.
- Directory deletion and recursive deletion are not supported.
- Delete requests move a file to a connector-managed quarantine folder inside the granted location; they do not immediately permanently erase it.
- Every attempted file-changing action is recorded in the local activity log.
- The connector does not send file contents to Render. The UI must call the connector directly for device files.

## Pairing and reconnection

On first launch the connector prints a one-time pairing code. When the user chooses Connect Device, the connector first requests a native local confirmation dialog; if the host cannot show it, the user can enter the printed code instead. The connector consumes the code when used and returns a random bearer token stored by the browser. Subsequent visits reuse the token and check `/v1/connection`; they do not pair again unless local browser storage is cleared, the connector state is reset, or the user revokes pairing.

## Browser compatibility

The hosted site may need browser permission for requests to loopback/private-network addresses. The connector adds CORS and Private Network Access response headers for configured origins, but browser policies differ. If the browser blocks the connection, the app must show an actionable error rather than claiming the device is connected. A packaged desktop shell can provide a more reliable bridge later.

## Configuration

- `LAZ_CONNECTOR_HOST` defaults to `127.0.0.1`; non-loopback binding is rejected.
- `LAZ_CONNECTOR_PORT` defaults to `43179`.
- `LAZ_CONNECTOR_ALLOWED_ORIGINS` accepts a comma-separated list. Defaults cover the Laz Helper Render origin and local development origins.
- State is stored under the operating system's per-user application configuration directory. On POSIX systems the state file is restricted to the current user where supported.


## Local Ask/voice and task planning

The Ask/voice UI has two additional device-local modes: **Ask my device files** and **Plan a task on my device**. They call `/v1/assistant/ask` and `/v1/assistant/plan` on the paired loopback connector, not the hosted Render API. The local connector sends bounded text excerpts or a file inventory to an Ollama-compatible model on loopback only. The default is `gemma3:1b` at `http://127.0.0.1:11434/api/generate`; configure `LAZ_CONNECTOR_OLLAMA_URL` and `LAZ_CONNECTOR_OLLAMA_MODEL` if needed. Remote model URLs are rejected by the connector to prevent device content from being sent off-device.

Install and start Ollama on the same device, then pull the configured model (default `gemma3:1b`). The connector does not silently install a model or download large model weights. If the local model is unavailable, device-local Ask/plan requests return an actionable error; the existing hosted workspace modes remain separate.

Device task planning is proposal-only. The user must review and confirm each operation; every operation is revalidated by the connector's permission, path, collision, and approval guards immediately before execution. Only a bounded set of UTF-8 text formats is included in local question context; binary files and PDFs are listed as inventory items but are not text-extracted by this first integration.
