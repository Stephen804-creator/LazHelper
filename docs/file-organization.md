# File Organization

Laz Helper provides a review-first workflow for organizing files inside a configured workspace.

## Preview before moving

The organization planner uses the configured category rules to propose a destination for each selected file. It displays the source, proposed destination, and status so the user can review the plan before applying it.

Only items explicitly approved by the user are eligible to move. Uncertain items and destination conflicts are not treated as ready moves.

## Duplicate discovery

Laz Helper can compare file hashes to identify exact, byte-for-byte duplicates. Results are intended to help the user decide what to review. Duplicate detection does not delete files.

## Review queue

Files that do not match an organization rule can be placed in the review queue. Users can mark entries as reviewed or dismiss them without moving or deleting the files.

## Operation journal and undo

Successful approved moves are recorded in the local operation journal. Undo attempts to restore a file to its original path and refuses to overwrite an existing destination. Recovery depends on the file and original location still being available; the journal is not a backup system.

## Preferences

Organization rules and supported preferences are stored locally. Review the configured workspace and category rules before applying a plan.

## Safety behavior

- Scanning and plan generation do not change file locations.
- File moves require explicit approval.
- Existing destination files are not silently overwritten.
- Duplicate discovery is read-only.
- The application does not provide a file-deletion operation.
- All file operations must remain within the configured workspace.
