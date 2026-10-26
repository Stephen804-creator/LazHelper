# Laz Helper — Units 1–4

This document records the first implementation block for the device-connected Laz Helper experience. These units extend the existing repository; they do not authorize a visual redesign or removal of existing product capabilities.

## Unit 1 — Audit and preserve the interface

### Audit findings for the preserved Ask/voice interface
- The richer staged interface in `build/stage-pq-clean-integration` uses `static/index.html` with the staged Ask/voice, workspace, tools, permission, profile, plan, and activity modules.
- The existing Ask/voice and permission experience is preserved. The connector panel is an additive module; it does not replace the chat/voice interface or add a plus/upload control.
- The FastAPI app in `app/main.py` serves the hosted website and the existing workspace API.
- `app/config.py` points the hosted API at its configured server-side workspace. On Render, that is the Render service's filesystem, not the visitor's private device.
- The existing local AI adapter uses an Ollama-compatible endpoint. A Render deployment cannot assume that the visitor's local Ollama service is available to the hosted server.
- The repository already has bounded scanning, document extraction, duplicate discovery, review-first move planning, a move journal, and path-safety checks. Those remain in place.
- A local connector must not turn the public Render backend into a proxy with unrestricted access to the user's computer.

### Preservation rules
1. Do not replace or restyle the existing interface as part of Units 1–4.
2. Do not add a plus/upload control as a substitute for device connection.
3. Add the device connection flow as a separate, reusable UI module.
4. Keep the hosted workspace and the user's device filesystem as separate trust boundaries.
5. Keep scanning read-only and all file-changing operations reviewable, permission-checked, and logged.
6. Do not claim that the browser or Render can silently install software or read arbitrary local files.

## Unit 2 — Local connector architecture

The hosted website remains the UI and orchestration surface. The Laz Connector is a separately installed local process in the same repository. It binds to loopback only, exposes a small versioned API, checks the requesting website origin, and requires a pairing token for file and permission APIs.

The connector stores grants and activity on the user's device. A grant is limited to an explicitly selected file or folder and a separate set of capabilities. System/protected locations are rejected. Browser access to the connector is subject to browser private-network/CORS rules and operating-system approval.

## Unit 3 — Local connector foundation

The first connector implementation includes:
- loopback-only HTTP service;
- health and identity endpoint;
- one-time pairing code, persisted pairing token, and authenticated API calls;
- native file/folder picker where the host supports a graphical desktop;
- file/folder grants with separate read, create, edit, move, rename, and delete capabilities;
- path-boundary and symlink checks;
- safe create/edit/move/rename operations that reject destination collisions;
- delete-to-quarantine rather than immediate permanent deletion;
- approval-mode settings and an activity journal;
- test coverage for pairing, permissions, protected paths, and file-operation safety.

## Unit 4 — Connect Device and reconnect

The web module:
- shows a first-visit explanation that can be dismissed;
- keeps a persistent Connect Device control available;
- checks whether the local connector is running;
- provides an installation/release route when it is missing;
- pairs using the one-time code shown by the local connector;
- stores the paired token in browser-local storage and reconnects automatically on later visits;
- shows disconnected/reconnect status if the connector is stopped or removed;
- exposes permission scope, folder/file selection, capability checkboxes, approval mode, grant revocation, and recent activity.

## Known constraints

- A browser-only PWA cannot install or run a local executable by itself.
- A web page cannot bypass OS permissions. The local connector must be installed and running, and the user must approve installation and the requested file/folder grants.
- Native file picking depends on a desktop GUI. Headless environments may require the CLI/configuration route.
- Standalone executable release packages are built by the repository workflow when a connector release tag is published; until a release exists, the release page may not contain a downloadable binary.
- These units do not yet replace the existing workspace APIs with connector-backed file operations. The connector API is the safe local foundation; the next integration step must route file requests through the paired connector rather than sending private file contents to Render.
