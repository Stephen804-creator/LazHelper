# Unit 1 — Product specification
## Promise
LazyDesk helps people understand cluttered folders and makes safe, reviewable recommendations without taking control away from the user.
## Workflow
Scan → Understand → Recommend → Review → Organise → Undo. Units 1–5 deliver the first four stages as a read-only foundation.
## Users
People with crowded Downloads folders, confusing documents, scattered projects, and spreadsheets they find hard to interpret.
## In scope
- Scan only an explicitly configured workspace.
- Inventory file names, types, sizes, and timestamps.
- Extract bounded content from supported documents, spreadsheets, slides, images, source text, and ZIP inventories.
- Optionally ask a local model for a summary, category, evidence, and descriptive filename.
- Display extracted content and recommendations for human review.
## Out of scope
Automatic move/rename/delete, duplicate removal, inbox watcher, personalisation, cloud upload, OCR pipeline, and undo journal.
## Acceptance criteria
1. UI loads and explains safety.
2. Path traversal is rejected; symlinks are not followed.
3. Scan/extraction do not alter file bytes.
4. Spreadsheet previews show sheet/column/row information where available.
5. Unsupported, oversized, encrypted, or malformed files return understandable errors.
6. AI outage does not disable scanning/extraction.
7. Model output is validated and treated as untrusted advice.
8. No AI output initiates filesystem operations.
