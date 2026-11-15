# Product Overview

Laz Helper helps people understand cluttered workspaces and organize files with less manual effort. It scans a configured workspace, extracts useful information from supported file formats, and presents recommendations people can review before deciding what to do.

## Who it helps

Laz Helper is designed for people managing busy Downloads folders, mixed document collections, spreadsheets, reports, and other local files that are difficult to navigate.

## How it works

1. **Scan** a configured workspace within defined limits.
2. **Understand** supported documents through extracted text and metadata.
3. **Get recommendations** with AI-assisted descriptions and organization suggestions.
4. **Review** proposed destinations, duplicate matches, and files that need attention.
5. **Organise** the file moves the user approves.
6. **Recover** supported moves through the operation journal when the original location is available.

## Core capabilities

- Workspace scanning and supported document extraction.
- Ollama-powered file summaries and organization recommendations.
- Preview-first file organization with explicit approval for moves.
- Exact duplicate discovery.
- A review queue for uncertain categories.
- Local operation history and undo for supported moves.
- Configurable organization preferences.
- Sloth Mode scheduled inbox reviews.
- Metadata-based workspace insights.

## Product principles

Laz Helper keeps users in control of file changes. Scanning and analysis leave files in place, recommendations support informed decisions, destination conflicts are handled without overwriting existing files, and scheduled reviews help users decide what needs attention.

## Operating model

Laz Helper can run locally or as a hosted service. It only inspects the workspace configured on the backend host: a local run can use a local folder, while a hosted run uses the server's workspace and cannot access a visitor's device files. Workspace API routes require a bearer token. Application state uses SQLite by default and PostgreSQL when `DATABASE_URL` is configured. AI-assisted recommendations send extracted content to the configured Ollama-compatible endpoint; workspace insights are generated from file metadata.
