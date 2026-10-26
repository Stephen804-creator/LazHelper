# Product Overview

Laz Helper helps people understand cluttered workspaces and organize files with less manual effort. It scans a configured workspace, extracts useful information from supported file formats, and presents recommendations that people can review before deciding what to do.

## Who it helps

Laz Helper is designed for people managing busy Downloads folders, mixed document collections, spreadsheets, reports, and other local files that are difficult to navigate.

## How it works

1. **Scan** a configured workspace within defined limits.
2. **Inspect** supported documents and view extracted text or metadata.
3. **Understand** files with optional AI-assisted descriptions and suggestions.
4. **Review** proposed destinations, duplicate matches, and files that need attention.
5. **Organize** only the file moves the user explicitly approves.
6. **Recover** supported moves through the local operation journal when the original location is available.

## Main capabilities

- Bounded workspace scanning and supported document extraction.
- Optional Ollama-powered file summaries and organization recommendations.
- Preview-first file organization with explicit approval for moves.
- Exact duplicate detection that reports matches without deleting files.
- A review queue for uncertain categories.
- Local operation history and undo for supported moves.
- Configurable organization preferences.
- Optional Sloth Mode scheduled inbox reviews.
- Metadata-based workspace insights.

## Product principles

Laz Helper keeps the user in control of file changes. Scanning and analysis do not move files. Recommendations are advisory, destination conflicts are refused, and scheduled reviews produce reports rather than silently reorganizing a workspace.

## Current operating model

Laz Helper is a local-first application built with FastAPI and a browser interface. File-operation history and preferences use local SQLite state. AI recommendations are optional and use the configured Ollama service. Review the [security and privacy guidance](security-and-privacy.md) before using the application with sensitive files or considering any deployment beyond a local environment.
