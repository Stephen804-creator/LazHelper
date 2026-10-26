# LazHelper Units 6–10

## Unit 6 — Review-first organisation
Build a proposed destination for each selected file using editable category rules. The plan is a preview; only explicitly approved items can be applied. Destination collisions are rejected and files are never overwritten. The organiser is confined to the configured workspace.

## Unit 7 — Duplicate and clutter discovery
Hash eligible files with SHA-256 in bounded chunks and group exact byte-for-byte matches. A match is a review signal, not permission to delete. No fuzzy duplicate claims are made.

## Unit 8 — “Not Sure” review queue
Files with no matching category rule can be added to a persistent review queue. The user can mark an item reviewed or dismiss it. Queue decisions do not move or delete files.

## Unit 9 — Operation journal and undo
Record every successful user-approved move. Undo restores the source path only when that path is free; collisions are refused. Journal records live in a local SQLite state file and are not sent to a service. This is a practical local undo journal, not a guarantee against disk failure or external changes.

## Unit 10 — Personal preferences
Persist user category rules and organisation preferences locally. Preference input is validated and limited. The defaults remain conservative and can be reset by deleting the local preference state after stopping the app.

## Safety contract
- Scan and duplicate discovery are read-only.
- Plan generation never mutates files.
- Moves require a separate explicit apply call with per-item approval.
- The hosted workspace API does not expose a delete endpoint. The separate local connector has a delete-to-quarantine operation, gated by a delete grant and explicit approval.
- Undo never overwrites an existing file.
- The original local workspace prototype has no authentication and is not suitable for public exposure. The separate connector has its own pairing/token checks and must bind to loopback only.
