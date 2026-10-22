"""Local-only workspace summaries. Does not transmit content to an AI provider."""
from collections import Counter, defaultdict
from pathlib import Path
from . import config
from .scanner import safe_workspace_path, scan_folder

def workspace_insights(relative_path="."):
    folder = safe_workspace_path(relative_path)
    result = scan_folder(relative_path)
    by_extension = Counter()
    by_folder = Counter()
    total_bytes = 0
    files = []
    for f in result["files"]:
        ext = f.extension.lower() or "[no extension]"
        by_extension[ext] += 1
        parent = str(Path(f.relative_path).parent)
        by_folder[parent] += 1
        total_bytes += f.size_bytes
        files.append({"path": f.relative_path, "extension": ext, "size_bytes": f.size_bytes})
    largest = sorted(files, key=lambda x: x["size_bytes"], reverse=True)[:10]
    folder_summary = [
        {"folder": name, "file_count": count,
         "summary": f"{count} file(s); common types: " + ", ".join(ext for ext, _ in by_extension.most_common(3))}
        for name, count in by_folder.most_common(20)
    ]
    return {
        "root": result["scanned_root"], "files_count": len(files), "total_bytes": total_bytes,
        "extension_counts": dict(by_extension.most_common()),
        "folder_summaries": folder_summary, "largest_files": largest,
        "truncated": result["truncated"],
        "message": "Insights are based on filenames, extensions and file sizes only. No file content was uploaded or changed."
    }
