import json
from pathlib import Path

import pytest

from app import config, organizer
from app import stage_l


@pytest.fixture
def plan_workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "notes.txt").write_text("Cloud computing notes.", encoding="utf-8")
    (root / "table.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"test_{tmp_path.name}")
    return root


def test_json_export_includes_schema_metadata_confidence_and_is_read_only(plan_workspace):
    result = stage_l.export_plan(["notes.txt"], "json")
    payload = json.loads(result["content"])
    assert payload["schema"] == "lazhelper.organisation-plan"
    assert payload["format_version"] == 1
    assert payload["items"][0]["file_metadata"]["sha256"]
    assert 0 <= payload["items"][0]["confidence"] <= 1
    assert result["files_changed"] is False
    assert (plan_workspace / "notes.txt").exists()


def test_csv_export_and_import_preview(plan_workspace):
    exported = stage_l.export_plan(["notes.txt"], "csv")
    assert exported["content"].startswith("source,destination,status,reason,confidence,file_metadata")
    imported = stage_l.import_plan(exported["content"], "csv")
    assert imported["valid_count"] == 1
    assert imported["files_changed"] is False
    assert imported["apply_allowed"] is False
    assert imported["items"][0]["approved"] is False


def test_import_flags_changed_source(plan_workspace):
    exported = stage_l.export_plan(["notes.txt"], "json")
    (plan_workspace / "notes.txt").write_text("Changed after plan export.", encoding="utf-8")
    imported = stage_l.import_plan(exported["content"])
    assert imported["stale_count"] == 1
    assert imported["items"][0]["source_changed"] is True
    assert imported["items"][0]["status"] == "stale"


def test_import_flags_destination_collision(plan_workspace):
    exported = stage_l.export_plan(["notes.txt"], "json")
    (plan_workspace / "Documents").mkdir()
    (plan_workspace / "Documents" / "notes.txt").write_text("existing", encoding="utf-8")
    imported = stage_l.import_plan(exported["content"])
    assert imported["conflict_count"] == 1
    assert imported["items"][0]["destination_exists"] is True


def test_import_rejects_bad_schema_and_unsafe_paths(plan_workspace):
    with pytest.raises(ValueError, match="Unrecognised plan schema"):
        stage_l.import_plan(json.dumps({"items": []}))
    payload = {"schema": "lazhelper.organisation-plan", "format_version": 1,
               "items": [{"source": "../outside.txt", "destination": "Documents/outside.txt"}]}
    imported = stage_l.import_plan(json.dumps(payload))
    assert imported["error_count"] == 1
    assert imported["valid_count"] == 0
    assert imported["files_changed"] is False


def test_import_handles_missing_source_without_modifying_workspace(plan_workspace):
    payload = {"schema": "lazhelper.organisation-plan", "format_version": 1,
               "items": [{"source": "missing.txt", "destination": "Documents/missing.txt"}]}
    before = sorted(p.relative_to(plan_workspace).as_posix() for p in plan_workspace.rglob("*"))
    result = stage_l.import_plan(json.dumps(payload))
    after = sorted(p.relative_to(plan_workspace).as_posix() for p in plan_workspace.rglob("*"))
    assert result["error_count"] == 1
    assert before == after


def test_json_export_rejects_invalid_format(plan_workspace):
    with pytest.raises(ValueError, match="Export format"):
        stage_l.export_plan(["notes.txt"], "xml")
