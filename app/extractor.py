"""Bounded read-only extraction; document text and code are never executed."""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import PurePosixPath

from . import config
from .scanner import open_workspace_file


TEXT_EXTS = {
    ".txt", ".md", ".py", ".js", ".ts", ".html", ".css", ".json",
    ".xml", ".yaml", ".yml", ".toml", ".java", ".c", ".h", ".cpp",
    ".go", ".rs", ".sh", ".sql",
}
MAX_ARCHIVE_ENTRIES = 5000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


def clip(text):
    return (text or "")[:config.MAX_TEXT_CHARS]


def decode(data):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _bounded_read(stream):
    data = stream.read(config.MAX_FILE_BYTES + 1)
    if len(data) > config.MAX_FILE_BYTES:
        raise ValueError("File exceeds configured size limit.")
    return data


def _check_archive_limits(stream):
    """Reject oversized archive metadata and extreme compression ratios."""
    try:
        with zipfile.ZipFile(stream) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise ValueError("Archive contains too many entries to inspect safely.")
            total_size = sum(info.file_size for info in infos)
            if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ValueError("Archive expands beyond the configured inspection limit.")
            for info in infos:
                if info.file_size > 0:
                    if info.compress_size <= 0:
                        raise ValueError("Archive contains an invalid compressed entry.")
                    if info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                        raise ValueError("Archive compression ratio is too high to inspect safely.")
    except zipfile.BadZipFile as exc:
        raise ValueError("Archive is damaged or invalid.") from exc
    finally:
        stream.seek(0)


def extract_file(relative_path):
    ext = PurePosixPath(str(relative_path)).suffix.lower()

    with open_workspace_file(relative_path) as stream:
        if ext in TEXT_EXTS:
            return {
                "kind": "text",
                "text": clip(decode(_bounded_read(stream))),
                "details": {"format": ext, "execution": "never"},
            }

        if ext == ".rtf":
            raw = decode(_bounded_read(stream))
            try:
                from striprtf.striprtf import rtf_to_text
                text = rtf_to_text(raw)
            except ImportError:
                text = re.sub(r"\\'[0-9a-fA-F]{2}|\\[a-zA-Z]+-?\d* ?|[{}]", " ", raw)
            return {
                "kind": "text",
                "text": clip(text),
                "details": {"format": "RTF"},
            }

        if ext == ".csv":
            raw = decode(_bounded_read(stream))
            try:
                dialect = csv.Sniffer().sniff(raw[:8192], delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            rows = csv.reader(io.StringIO(raw), dialect)
            preview = []
            count = 0
            for row in rows:
                count += 1
                if len(preview) < 16:
                    preview.append([str(value)[:250] for value in row[:24]])
                if count >= 20000:
                    break
            headers = preview[0] if preview else []
            return {
                "kind": "spreadsheet",
                "text": clip(json.dumps({
                    "headers": headers,
                    "preview_rows": preview[:8],
                    "sampled_rows": count,
                    "count_capped_at": 20000,
                }, ensure_ascii=False)),
                "details": {
                    "format": "CSV",
                    "sampled_rows": count,
                    "columns": len(headers),
                },
            }

        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise ValueError("Encrypted PDFs are not opened.")
            chunks = []
            total_chars = 0
            for index, page in enumerate(reader.pages[:50]):
                text = page.extract_text() or ""
                chunks.append(f"[Page {index + 1}]\n{text}")
                total_chars += len(text)
                if total_chars >= config.MAX_TEXT_CHARS:
                    break
            return {
                "kind": "document",
                "text": clip("\n\n".join(chunks)),
                "details": {
                    "format": "PDF",
                    "pages_total": len(reader.pages),
                    "pages_read": len(chunks),
                },
            }

        if ext in {".docx", ".xlsx", ".pptx", ".zip"}:
            _check_archive_limits(stream)

        if ext == ".docx":
            from docx import Document
            doc = Document(stream)
            chunks = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            for table in doc.tables[:20]:
                chunks.append("[Table]\n" + "\n".join(
                    " | ".join(cell.text[:200] for cell in row.cells[:20])
                    for row in table.rows[:100]
                ))
            return {
                "kind": "document",
                "text": clip("\n".join(chunks)),
                "details": {
                    "format": "DOCX",
                    "paragraphs": len(doc.paragraphs),
                    "tables": len(doc.tables),
                },
            }

        if ext == ".xlsx":
            from openpyxl import load_workbook
            workbook = load_workbook(stream, read_only=True, data_only=True)
            sheets = []
            try:
                for worksheet in workbook.worksheets[:20]:
                    rows = [
                        [str(value)[:150] if value is not None else "" for value in row]
                        for row in worksheet.iter_rows(
                            max_row=150, max_col=30, values_only=True
                        )
                    ]
                    sheets.append({
                        "sheet": worksheet.title,
                        "reported_rows": worksheet.max_row,
                        "reported_columns": worksheet.max_column,
                        "preview_rows": rows[:10],
                    })
            finally:
                workbook.close()
            return {
                "kind": "spreadsheet",
                "text": clip(json.dumps({"sheets": sheets}, ensure_ascii=False, default=str)),
                "details": {"format": "XLSX", "sheets": len(sheets), "read_only": True},
            }

        if ext == ".xls":
            import xlrd
            book = xlrd.open_workbook(
                file_contents=_bounded_read(stream),
                on_demand=True,
            )
            sheets = []
            try:
                for sheet in book.sheets()[:20]:
                    rows = [
                        [str(sheet.cell_value(row, col))[:150]
                         for col in range(min(sheet.ncols, 30))]
                        for row in range(min(sheet.nrows, 100))
                    ]
                    sheets.append({
                        "sheet": sheet.name,
                        "rows": sheet.nrows,
                        "columns": sheet.ncols,
                        "preview_rows": rows[:10],
                    })
            finally:
                book.release_resources()
            return {
                "kind": "spreadsheet",
                "text": clip(json.dumps({"sheets": sheets}, ensure_ascii=False)),
                "details": {"format": "XLS legacy", "sheets": len(sheets), "read_only": True},
            }

        if ext == ".pptx":
            from pptx import Presentation
            presentation = Presentation(stream)
            chunks = []
            total_chars = 0
            for index, slide in enumerate(presentation.slides[:80]):
                lines = [
                    shape.text for shape in slide.shapes
                    if getattr(shape, "has_text_frame", False) and shape.text.strip()
                ]
                text = "\n".join(lines)
                chunks.append(f"[Slide {index + 1}]\n{text}")
                total_chars += len(text)
                if total_chars >= config.MAX_TEXT_CHARS:
                    break
            return {
                "kind": "presentation",
                "text": clip("\n\n".join(chunks)),
                "details": {
                    "format": "PPTX",
                    "slides_total": len(presentation.slides),
                    "slides_read": len(chunks),
                },
            }

        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            from PIL import Image
            with Image.open(stream) as image:
                if image.width * image.height > 40_000_000:
                    raise ValueError("Image dimensions exceed the inspection limit.")
                info = {
                    "format": image.format,
                    "width": image.width,
                    "height": image.height,
                    "mode": image.mode,
                    "ocr": "not enabled; metadata only",
                }
            return {"kind": "image", "text": json.dumps(info), "details": info}

        if ext == ".zip":
            items = []
            with zipfile.ZipFile(stream) as archive:
                for info in archive.infolist()[:500]:
                    if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                        continue
                    name = info.filename.replace("\\", "/")
                    parts = PurePosixPath(name).parts
                    if name.startswith("/") or ".." in parts:
                        name = "[unsafe path omitted]"
                    items.append({
                        "name": name[:240],
                        "size": info.file_size,
                        "directory": info.is_dir(),
                    })
            return {
                "kind": "archive_inventory",
                "text": clip(json.dumps(items, ensure_ascii=False)),
                "details": {
                    "format": "ZIP inventory only",
                    "entries_listed": len(items),
                    "extracted": False,
                },
            }

    raise ValueError("This file type is not supported for content inspection.")
