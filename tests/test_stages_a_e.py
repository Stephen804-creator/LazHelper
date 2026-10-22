from pathlib import Path

import pytest

from app import config
from app.workspace_intelligence import (
    content_search,
    duplicate_insights,
    file_relationships,
    knowledge_map,
    workspace_health_report,
)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    (root / "Research Report.txt").write_text(
        "Cloud computing uses virtualized resources and network services. "
        "This report explains cloud computing architecture.", encoding="utf-8"
    )
    (root / "Research Report Final.txt").write_text(
        "Cloud computing uses virtualized resources and network services. "
        "This report explains cloud computing architecture.", encoding="utf-8"
    )
    (root / "cloud_notes.md").write_text(
        "Cloud computing notes: virtual machines, networks, and storage.", encoding="utf-8"
    )
    (root / "document1.txt").write_text("A generic filename needs review.", encoding="utf-8")
    (root / "copy_of_notes.txt").write_text("A generic copy for duplicate testing.", encoding="utf-8")
    (root / "same_copy.txt").write_text("A generic copy for duplicate testing.", encoding="utf-8")
    (root / "folder").mkdir()
    (root / "folder" / "meeting.txt").write_text("Project meeting notes.", encoding="utf-8")
    return root


def test_relationships_explain_evidence_and_do_not_change_files(workspace):
    before = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file())
    result = file_relationships(".")
    after = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file())
    assert result["relationships"]
    assert any("shared terms" in " ".join(edge["evidence"]) for edge in result["relationships"])
    assert before == after


def test_duplicate_insights_separate_exact_matches_and_version_candidates(workspace):
    result = duplicate_insights(".")
    assert any(len(group["files"]) == 2 for group in result["exact_duplicate_groups"])
    assert any(group["base_name"] == "research report" for group in result["version_families"])
    assert result["message"].startswith("Detection only")


def test_content_search_finds_content_and_filename_matches(workspace):
    result = content_search("virtualized resources")
    assert any(row["path"] == "Research Report.txt" and row["match"] == "content" for row in result["results"])
    assert result["readable_files_inspected"] > 0
    assert "not sent to an AI service" in result["message"]


def test_search_rejects_empty_or_excessively_long_queries():
    with pytest.raises(ValueError):
        content_search(" ")
    with pytest.raises(ValueError):
        content_search("x" * 301)


def test_knowledge_map_has_nodes_and_relationship_edges(workspace):
    result = knowledge_map(".")
    assert result["node_count"] >= 7
    assert result["nodes"]
    assert all("id" in node and "label" in node for node in result["nodes"])
    assert all("source" in edge and "target" in edge for edge in result["edges"])


def test_health_report_flags_generic_names_without_destructive_actions(workspace):
    before = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file())
    result = workspace_health_report(".")
    after = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file())
    assert any(row["kind"] == "generic_name" and row["path"] == "document1.txt" for row in result["findings"])
    assert result["files_count"] == len(before)
    assert before == after


def test_workspace_intelligence_rejects_paths_outside_workspace(workspace):
    with pytest.raises(ValueError):
        file_relationships("../")
