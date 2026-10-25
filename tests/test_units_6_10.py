from pathlib import Path
import pytest
from app import config, organizer

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "incoming").mkdir()
    (root / "incoming" / "report.txt").write_text("quarterly report", encoding="utf-8")
    (root / "incoming" / "copy.txt").write_text("quarterly report", encoding="utf-8")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"t_{abs(hash(tmp_path.name))}")
    return root

def test_plan_is_preview_only(workspace):
    before = (workspace / "incoming" / "report.txt").read_bytes()
    result = organizer.build_plan(["incoming/report.txt"])
    assert result["plan"][0]["status"] == "ready"
    assert result["message"].startswith("Preview only")
    assert (workspace / "incoming" / "report.txt").read_bytes() == before
    assert not (workspace / "Documents" / "report.txt").exists()

def test_apply_requires_explicit_approval(workspace):
    result = organizer.apply_plan([{"source":"incoming/report.txt","destination":"Documents/report.txt","approved":False}])
    assert result["files_changed"] == 0
    assert (workspace / "incoming" / "report.txt").exists()

def test_apply_and_undo_are_journalled(workspace):
    result = organizer.apply_plan([{"source":"incoming/report.txt","destination":"Documents/report.txt","approved":True}])
    assert result["files_changed"] == 1
    assert (workspace / "Documents" / "report.txt").read_text(encoding="utf-8") == "quarterly report"
    operation_id = result["completed"][0]["id"]
    undone = organizer.undo_operation(operation_id)
    assert undone["restored_path"] == "incoming/report.txt"
    assert (workspace / "incoming" / "report.txt").exists()
    assert not (workspace / "Documents" / "report.txt").exists()

def test_duplicate_finder_only_reports_exact_matches(workspace):
    result = organizer.find_duplicates(".")
    assert result["duplicate_files"] == 2
    assert len(result["groups"]) == 1
    assert (workspace / "incoming" / "report.txt").exists()
    assert (workspace / "incoming" / "copy.txt").exists()

def test_preferences_reject_unsafe_category_names(workspace):
    with pytest.raises(ValueError):
        organizer.save_preferences({"category_rules":{"../outside":[".txt"]}})

def test_unknown_extension_goes_to_review_queue(workspace):
    (workspace / "incoming" / "mystery.bin").write_bytes(b"unknown")
    result = organizer.build_plan(["incoming/mystery.bin"])
    assert result["plan"][0]["status"] == "needs_review"
    assert any(item["path"] == "incoming/mystery.bin" for item in organizer.list_queue())
