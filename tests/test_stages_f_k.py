import json
import zipfile
from pathlib import Path

import pytest

from app import config, organizer, extended_workspace as ew


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "Cloud Computing Notes.txt").write_text(
        "Cloud computing provides on-demand network access to shared configurable resources. "
        "Virtual machines and storage are common cloud computing services.", encoding="utf-8"
    )
    (root / "Research Final.txt").write_text(
        "Research findings and cloud computing architecture are documented here.", encoding="utf-8"
    )
    (root / "Research Updated.txt").write_text(
        "Research findings and cloud computing architecture are documented here.", encoding="utf-8"
    )
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(ew, "DB_SCHEMA", f"test_{tmp_path.name}_workspace")
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"test_{tmp_path.name}_organizer")
    return root


def test_recovery_export_formats_and_invalid_format(workspace):
    json_result = ew.recovery_history(export_format="json")
    csv_result = ew.recovery_history(export_format="csv")
    assert json_result["format"] == "json"
    assert csv_result["content"].startswith("id,action,source_path")
    with pytest.raises(ValueError):
        ew.recovery_history(export_format="xml")


def test_project_workspace_metadata_and_overview_do_not_create_folders(workspace):
    before = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*"))
    project = ew.create_project({
        "name": "Cloud Computing", "kind": "study", "description": "Course notes",
        "folder_path": ".", "tags": ["cloud", "ESUT"],
        "structure": ["Lecture Notes", "Assignments", "Research"],
    })
    assert project["name"] == "Cloud Computing"
    assert project["suggested_structure"] == ["Lecture Notes", "Assignments", "Research"]
    overview = ew.project_overview(project["id"])
    assert overview["files_count"] >= 3
    assert "not created automatically" in overview["message"]
    after = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*"))
    assert before == after


def test_project_rejects_path_escape(workspace):
    with pytest.raises(ValueError):
        ew.create_project({"name": "Unsafe", "folder_path": "../"})


def test_archive_inventory_does_not_extract_and_flags_traversal(workspace):
    archive = workspace / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("notes/readme.txt", "Cloud computing archive notes.")
        zf.writestr("../outside.txt", "must not be extracted")
    before = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*"))
    result = ew.inspect_archive("bundle.zip", preview_text=True)
    after = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*"))
    assert result["extracted"] is False
    assert result["flagged_entries"] == 1
    assert any("unsafe path" in entry["warnings"] for entry in result["entries"])
    assert any(entry.get("text_preview") for entry in result["entries"])
    assert before == after


def test_archive_rejects_non_zip(workspace):
    with pytest.raises(ValueError):
        ew.inspect_archive("Cloud Computing Notes.txt")


def test_natural_language_command_is_a_preview_only(workspace):
    result = ew.preview_command("find cloud computing notes", ".")
    assert result["understood"] is True
    assert result["intent"] == "search"
    assert result["parameters"]["query"] == "cloud computing notes"
    assert result["requires_confirmation"] is True
    assert ew.preview_command("delete every file", ".")["understood"] is False


def test_local_knowledge_returns_source_passages(workspace):
    result = ew.ask_local_knowledge("What services are common in cloud computing?")
    assert result["source_count"] > 0
    assert any("Cloud Computing Notes.txt" == source["path"] for source in result["sources"])
    assert "not sent to an AI service" in result["message"]


def test_workflow_only_allows_read_only_actions(workspace):
    workflow = ew.create_workflow({
        "name": "Weekly workspace review",
        "description": "Search and health check",
        "steps": [
            {"action": "search", "parameters": {"query": "cloud computing", "relative_path": "."}},
            {"action": "health_report", "parameters": {"relative_path": "."}},
        ],
    })
    result = ew.run_workflow(workflow["id"])
    assert len(result["results"]) == 2
    assert result["files_changed"] is False
    with pytest.raises(ValueError):
        ew.create_workflow({
            "name": "Unsafe workflow",
            "steps": [{"action": "delete", "parameters": {"relative_path": "."}}],
        })


def test_workflow_rejects_unknown_parameters(workspace):
    with pytest.raises(ValueError):
        ew.create_workflow({
            "name": "Bad search",
            "steps": [{"action": "search", "parameters": {"query": "notes", "shell": "rm -rf"}}],
        })


def test_delete_project_or_workflow_only_removes_metadata(workspace):
    original = workspace / "Cloud Computing Notes.txt"
    project = ew.create_project({"name": "Metadata only"})
    workflow = ew.create_workflow({
        "name": "Read-only", "steps": [{"action": "health_report", "parameters": {"relative_path": "."}}],
    })
    ew.delete_project(project["id"])
    ew.delete_workflow(workflow["id"])
    assert original.exists()
