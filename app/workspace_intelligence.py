"""Bounded, local-only workspace intelligence for LazHelper Stages A–E.

All paths are resolved through the existing workspace-confined scanner. These
features report suggestions only: they never move, rename, overwrite, or delete.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path
from typing import Any

from . import config
from .extractor import extract_file
from .scanner import scan_folder, safe_file_path, UnsafePath

_WORD = re.compile(r"[a-z0-9]{2,}", re.I)
_VERSION = re.compile(
    r"(?i)(?:[ _.-]+(?:final|finalized|updated|revised|revision|copy|backup|duplicate|old|new|v\d+(?:\.\d+)*|ver(?:sion)?[ _.-]*\d+|\(\d+\)|\d{4}[-_]?\d{2}[-_]?\d{2}))*$"
)
_GENERIC_NAMES = {
    "document", "document1", "file", "file1", "untitled", "new document",
    "scan", "image", "img", "download", "presentation", "workbook", "copy",
}
_TEXT_KINDS = {"text", "document", "spreadsheet", "presentation"}


def _files(relative_path: str = ".", limit: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result = scan_folder(relative_path)
    records = [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in result["files"]]
    if limit is not None:
        records = records[:max(1, min(limit, config.MAX_FILES))]
    return result, records


def _tokens(value: str) -> set[str]:
    return {word.casefold() for word in _WORD.findall(value or "") if word.casefold() not in {"the", "and", "for", "from", "with", "this", "that"}}


def _normalized_stem(name: str) -> str:
    stem = Path(name).stem.casefold().replace("_", " ").replace("-", " ")
    previous = None
    while previous != stem:
        previous, stem = stem, _VERSION.sub("", stem).strip(" ._-")
    return re.sub(r"\s+", " ", stem).strip()


def _extract_text(relative_path: str) -> tuple[str, str | None]:
    try:
        result = extract_file(relative_path)
        if result.get("kind") not in _TEXT_KINDS:
            return "", None
        return str(result.get("text") or "")[:config.MAX_TEXT_CHARS], None
    except Exception as exc:
        # Malformed or unsupported documents should not abort the whole workspace scan.
        return "", str(exc)[:180]


def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def file_relationships(relative_path: str = ".", max_files: int = 400) -> dict[str, Any]:
    """Find explainable candidate relationships using bounded filename/path evidence."""
    scan, files = _files(relative_path, max_files)
    token_index: dict[str, set[int]] = defaultdict(set)
    tokens_by_index: list[set[str]] = []
    stems: dict[str, list[int]] = defaultdict(list)
    parents: list[str] = []
    for index, item in enumerate(files):
        tokens = _tokens(Path(item["relative_path"]).as_posix().replace("/", " ") + " " + item["name"])
        tokens_by_index.append(tokens)
        for token in tokens:
            token_index[token].add(index)
        stems[_normalized_stem(item["name"])].append(index)
        parents.append(str(Path(item["relative_path"]).parent).casefold())

    pairs: set[tuple[int, int]] = set()
    for indexes in token_index.values():
        if len(indexes) > 1:
            ordered = sorted(indexes)
            # Avoid quadratic explosions in very common terms.
            for pos, left in enumerate(ordered):
                for right in ordered[pos + 1:pos + 21]:
                    pairs.add((left, right))
    for indexes in stems.values():
        if len(indexes) > 1:
            ordered = sorted(indexes)
            for pos, left in enumerate(ordered):
                for right in ordered[pos + 1:]:
                    pairs.add((left, right))

    relationships = []
    for left, right in sorted(pairs):
        a, b = files[left], files[right]
        shared = tokens_by_index[left] & tokens_by_index[right]
        overlap = _similarity(tokens_by_index[left], tokens_by_index[right])
        same_stem = bool(_normalized_stem(a["name"]) and _normalized_stem(a["name"]) == _normalized_stem(b["name"]))
        same_parent = parents[left] == parents[right]
        if not shared and not same_stem:
            continue
        score = min(0.99, 0.18 + overlap * 0.52 + (0.28 if same_stem else 0) + (0.10 if same_parent else 0))
        if score < 0.34:
            continue
        reasons = []
        if same_stem:
            reasons.append("names share the same base after common version/copy suffixes")
        if shared:
            reasons.append("shared terms: " + ", ".join(sorted(shared)[:6]))
        if same_parent:
            reasons.append("stored in the same folder")
        if Path(a["name"]).suffix.casefold() != Path(b["name"]).suffix.casefold():
            reasons.append("different file formats may represent companion materials")
        relationships.append({
            "source": a["relative_path"], "target": b["relative_path"],
            "score": round(score, 3), "confidence": "strong" if score >= 0.72 else "possible",
            "relationship": "version_or_copy" if same_stem else "related_material",
            "evidence": reasons,
        })
    relationships.sort(key=lambda row: (-row["score"], row["source"], row["target"]))
    return {
        "root": scan["scanned_root"], "files_considered": len(files),
        "relationships": relationships[:500], "relationship_count": len(relationships),
        "truncated": scan["truncated"] or len(scan["files"]) > len(files),
        "message": "Relationships are evidence-based suggestions from filenames and paths, not proof that files belong together. No files were changed.",
    }


def duplicate_insights(relative_path: str = ".", max_files: int = 250) -> dict[str, Any]:
    """Combine exact hashes, filename-version families, and cautious text similarity."""
    scan, files = _files(relative_path, max_files)
    root = config.ALLOWED_ROOT.resolve()
    exact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    versions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    text_items: list[tuple[dict[str, Any], set[str]]] = []
    errors = []
    checked = 0
    skipped_files = 0
    budget_limited = False
    bytes_hashed = 0
    hash_budget = 512 * 1024 * 1024
    for item in files:
        try:
            path = safe_file_path(item["relative_path"])
            size_bytes = path.stat().st_size
            if size_bytes > config.MAX_FILE_BYTES:
                skipped_files += 1
                continue
            if bytes_hashed + size_bytes > hash_budget:
                skipped_files += 1
                budget_limited = True
                continue
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            exact[digest.hexdigest()].append({"path": item["relative_path"], "size_bytes": size_bytes})
            bytes_hashed += size_bytes
            stem = _normalized_stem(path.name)
            if stem:
                versions[stem].append({"path": item["relative_path"], "name": path.name, "extension": path.suffix.casefold(), "size_bytes": path.stat().st_size})
            if item.get("readable") and len(text_items) < 120:
                text, error = _extract_text(item["relative_path"])
                if text:
                    text_items.append((item, _tokens(text) ))
                elif error and len(errors) < 10:
                    errors.append({"path": item["relative_path"], "reason": error})
            checked += 1
        except (OSError, UnsafePath, ValueError):
            continue

    exact_groups = [{"sha256": digest, "files": group, "count": len(group)}
                    for digest, group in exact.items() if len(group) > 1]
    version_groups = []
    for stem, group in versions.items():
        unique = {item["path"] for item in group}
        if len(unique) > 1:
            version_groups.append({"base_name": stem, "files": group, "count": len(unique),
                                   "reason": "Similar base filenames after common version/copy suffixes; inspect contents before deciding."})

    similar_content = []
    # Compare a bounded subset only. Similarity is a review hint, never an auto-merge.
    for i, (left, left_tokens) in enumerate(text_items):
        for right, right_tokens in text_items[i + 1:]:
            if left["relative_path"] == right["relative_path"]:
                continue
            ratio = _similarity(left_tokens, right_tokens)
            if ratio >= 0.82 and left_tokens and right_tokens:
                similar_content.append({"files": [left["relative_path"], right["relative_path"]],
                                        "token_jaccard": round(ratio, 3),
                                        "reason": "Extracted text has high token overlap; verify meaningful differences manually."})
    similar_content.sort(key=lambda row: -row["token_jaccard"])
    return {
        "root": scan["scanned_root"], "files_checked": checked, "files_skipped": skipped_files, "hash_budget_limited": budget_limited,
        "exact_duplicate_groups": exact_groups, "exact_duplicate_files": sum(g["count"] for g in exact_groups),
        "version_families": version_groups[:200], "similar_content_pairs": similar_content[:100],
        "truncated": scan["truncated"] or len(scan["files"]) > len(files) or budget_limited,
        "extraction_notes": errors,
        "message": "Detection only. Exact matches are byte-for-byte; version families and text similarity are candidates. Large files and files beyond the cumulative hash budget are skipped and reported. Nothing is renamed, merged, moved, or deleted.",
    }


def content_search(query: str, relative_path: str = ".", max_results: int = 50, max_files: int = 300) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise ValueError("Enter a search phrase or keyword.")
    if len(query) > 300:
        raise ValueError("Search query must be 300 characters or fewer.")
    scan, files = _files(relative_path, max_files)
    query_fold = query.casefold()
    query_tokens = _tokens(query)
    results = []
    inspected = 0
    for item in files:
        name = item["name"]
        path = item["relative_path"]
        filename_text = f"{name} {path}"
        name_match = query_fold in filename_text.casefold()
        content = ""
        content_error = None
        if item.get("readable") and item.get("size_bytes", 0) <= config.MAX_FILE_BYTES:
            content, content_error = _extract_text(path)
            inspected += 1
        content_fold = content.casefold()
        exact_match = bool(content and query_fold in content_fold)
        overlap = _similarity(query_tokens, _tokens(content)) if query_tokens and content else 0.0
        if name_match or exact_match or overlap >= 0.5:
            if exact_match:
                idx = content_fold.find(query_fold)
                start, end = max(0, idx - 100), min(len(content), idx + len(query) + 160)
                snippet = content[start:end].replace("\n", " ").strip()
                match_source = "content"
            elif overlap >= 0.5 and content:
                snippet = " ".join(content.split())[:220]
                match_source = "related content terms"
            else:
                snippet = filename_text
                match_source = "filename or path"
            results.append({"path": path, "name": name, "extension": item["extension"],
                            "size_bytes": item["size_bytes"], "match": match_source,
                            "score": round(max(1.0 if exact_match else 0.0, overlap, 0.9 if name_match else 0.0), 3),
                            "snippet": snippet, "content_note": content_error})
    results.sort(key=lambda row: (-row["score"], row["path"].casefold()))
    return {"query": query, "root": scan["scanned_root"], "results": results[:max(1, min(max_results, 100))],
            "result_count": min(len(results), max(1, min(max_results, 100))),
            "files_considered": len(files), "readable_files_inspected": inspected,
            "truncated": scan["truncated"] or len(scan["files"]) > len(files),
            "message": "Search is local to the configured workspace. Snippets may contain private document text; results are not sent to an AI service."}


def knowledge_map(relative_path: str = ".", max_files: int = 250) -> dict[str, Any]:
    scan, files = _files(relative_path, max_files)
    rel = file_relationships(relative_path, max_files)
    nodes = []
    for item in files:
        nodes.append({"id": item["relative_path"], "label": item["name"], "type": item["extension"] or "[no extension]",
                      "size_bytes": item["size_bytes"], "folder": str(Path(item["relative_path"]).parent)})
    edges = [{"source": item["source"], "target": item["target"], "label": item["relationship"],
              "score": item["score"], "evidence": item["evidence"]} for item in rel["relationships"][:400]]
    folder_counts = Counter(node["folder"] for node in nodes)
    folders = [{"id": "folder:" + name, "label": name, "type": "folder", "file_count": count}
               for name, count in folder_counts.most_common(100)]
    return {"root": scan["scanned_root"], "nodes": folders + nodes, "edges": edges,
            "node_count": len(folders) + len(nodes), "edge_count": len(edges),
            "truncated": scan["truncated"] or len(scan["files"]) > len(files),
            "message": "The map visualises candidate relationships from local file names and paths. It does not assert semantic certainty or change files."}


def workspace_health_report(relative_path: str = ".", max_files: int = 500) -> dict[str, Any]:
    scan, files = _files(relative_path, max_files)
    findings = []
    extension_counts = Counter()
    parent_counts = Counter()
    name_patterns = Counter()
    total_bytes = 0
    now = datetime.now(timezone.utc).timestamp()
    for item in files:
        path = Path(item["relative_path"])
        ext = item["extension"].casefold() or "[no extension]"
        parent = str(path.parent)
        extension_counts[ext] += 1
        parent_counts[parent] += 1
        total_bytes += item["size_bytes"]
        stem = path.stem.strip()
        if stem.casefold() in _GENERIC_NAMES or re.fullmatch(r"(?:document|file|img|image|scan|untitled)[ _-]?\d*", stem, re.I):
            findings.append({"kind": "generic_name", "severity": "low", "path": item["relative_path"],
                             "reason": "Filename is generic and may be difficult to find later.",
                             "suggestion": "Consider a descriptive name after reviewing the file content."})
        if item["size_bytes"] > min(config.MAX_FILE_BYTES * 0.75, 15 * 1024 * 1024):
            findings.append({"kind": "large_file", "severity": "low", "path": item["relative_path"],
                             "size_bytes": item["size_bytes"], "reason": "File is relatively large for this workspace scan.",
                             "suggestion": "Review whether the size is expected; do not delete solely because it is large."})
        if not item.get("readable"):
            findings.append({"kind": "unsupported_or_limited", "severity": "info", "path": item["relative_path"],
                             "reason": item.get("note") or "No configured content extractor for this format.",
                             "suggestion": "Review manually or add a safe extractor if this format matters."})
        try:
            modified = datetime.fromisoformat(item["modified_at"].replace("Z", "+00:00")).timestamp()
            if now - modified > 365 * 86400:
                findings.append({"kind": "older_file", "severity": "info", "path": item["relative_path"],
                                 "reason": "File has not been modified for more than a year.",
                                 "suggestion": "Check whether it is still relevant; age alone does not mean it is unnecessary."})
        except (ValueError, TypeError, KeyError):
            pass
        normalized = re.sub(r"\d+", "#", path.stem.casefold())
        if normalized:
            name_patterns[normalized] += 1
    for folder, count in parent_counts.items():
        if count >= 50:
            findings.append({"kind": "crowded_folder", "severity": "medium", "folder": folder, "file_count": count,
                             "reason": "This folder contains many files in the current scan.",
                             "suggestion": "Consider reviewing files in batches and proposing subfolders."})
    for pattern, count in name_patterns.most_common(50):
        if count >= 4 and len(pattern) >= 3:
            findings.append({"kind": "repeated_name_pattern", "severity": "info", "pattern": pattern, "count": count,
                             "reason": "Several files share a filename pattern.",
                             "suggestion": "Check whether these files belong to one project or represent versions."})
    findings.sort(key=lambda row: ({"medium": 0, "low": 1, "info": 2}.get(row.get("severity"), 3), row.get("path", row.get("folder", ""))))
    return {"root": scan["scanned_root"], "files_count": len(files), "total_bytes": total_bytes,
            "extension_counts": dict(extension_counts.most_common()),
            "findings": findings[:500], "finding_count": len(findings),
            "severity_counts": dict(Counter(row["severity"] for row in findings)),
            "truncated": scan["truncated"] or len(scan["files"]) > len(files),
            "message": "A review checklist, not a verdict. Findings are based on local metadata and bounded extraction; no files are modified or deleted."}
