# LazHelper Stages A–E: Workspace Intelligence

These stages extend the Units 1–13 foundation. They are read-only analysis features; they do not rename, move, overwrite, merge, or delete user files.

## Stage A — Intelligent file relationships

Endpoint: `GET /api/relationships?relative_path=.&max_files=400`

The service compares bounded filename and path tokens, normalized base names, and parent folders. Each candidate edge includes a score, relationship type, and explicit evidence. Scores are ranking hints, not calibrated probabilities. The service caps files considered and relationship output.

## Stage B — Duplicate and version insights

Endpoint: `POST /api/duplicates/insights` with JSON `{"relative_path":"."}`

The report separates:
- Exact duplicates, determined by SHA-256 byte hashes.
- Possible version families, based on common suffixes such as Final, Copy, or v2.
- Similar-content pairs, based on token Jaccard overlap in bounded extracted text.

Only a bounded number of files are considered for this report, and hashing has a cumulative byte budget. Similarity is a review hint; it does not prove equivalence. No merge, rename, move, or deletion is performed.

## Stage C — Unified content-aware search

Endpoint: `GET /api/search?query=cloud%20computing&relative_path=.&max_results=50`

Search checks filenames and paths first, then uses the existing bounded extractor for supported, readable files. Results include match type, a score for ordering, and a short snippet. The query is limited to 300 characters and results are capped. Snippets can contain private document text, so the interface renders them as text rather than HTML. The search does not send content to an AI service.

## Stage D — Workspace knowledge map

Endpoint: `GET /api/knowledge-map?relative_path=.&max_files=250`

Returns folder and file nodes plus evidence-backed candidate relationship edges. This is a lightweight graph data model for the interface and future graph visualisation; it does not claim that a filename relationship proves semantic relevance. Nodes and edges are bounded.

## Stage E — Workspace health report

Endpoint: `GET /api/health-report?relative_path=.&max_files=500`

Reports review suggestions such as generic filenames, relatively large files, unsupported or size-limited formats, files older than a year, crowded folders, and repeated filename patterns. File age or size is never treated as evidence that a file is disposable. Every finding is advisory.

## Safety and limits

- All requested paths pass through the existing workspace-confined scanner and reject parent traversal and symlinks.
- File and text extraction respects the existing configured file-size and text-size limits.
- Stages A, D, and E operate on bounded metadata and filenames. Stages B and C read file bytes or supported content locally within explicit limits.
- Search snippets may reveal document content to anyone who can access the local app. The existing app has no authentication; keep it bound to loopback and do not expose it directly to the internet.
- AI recommendations remain separate and optional. These stages do not submit file contents to Ollama or another model.
- Truncated responses explicitly report that results may be incomplete.
- Run `python -m pytest -q` and inspect the GitHub Actions result before treating this development branch as release-ready.
