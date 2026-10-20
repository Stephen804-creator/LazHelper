# LazyDesk Units 11–13

## Unit 11 — Sloth Mode
Sloth Mode can watch a designated folder on an opt-in interval and prepare an organisation review summary. It is disabled by default, validates that the inbox is inside the configured workspace, and never applies moves automatically. Each background pass reports files seen, files ready for review, uncertain items and conflicts. This is a process-local scheduler: it runs only while LazyDesk is running.

## Unit 12 — Digital Workspace Insights
Summarises counts by extension and folder, estimates total size, and lists the largest files. This initial Digital Mess Map is deliberately metadata-only; it does not upload file contents or claim semantic relationships it has not established.

## Unit 13 — Testing, Security and Recovery
Adds tests for Sloth Mode opt-in behaviour, invalid inbox paths, schedule bounds, metadata-only insights, path confinement, duplicate read-only behaviour, explicit move approval, collision refusal and journal undo. Review the CI results before merging.

## Operational boundary
The local application has no authentication. Bind it to loopback and never expose it to the public internet. Background review does not mean background file modification. A move is still a separate, explicit user-approved operation.
