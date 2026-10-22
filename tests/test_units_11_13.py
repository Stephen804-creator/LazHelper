import pytest
from app import config, organizer, sloth_mode, insights
from app.scanner import UnsafePath, safe_workspace_path

@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "inbox").mkdir()
    (root / "inbox" / "note.txt").write_text("A small note", encoding="utf-8")
    (root / "reports").mkdir()
    (root / "reports" / "table.csv").write_text("name,value\nalpha,1\n", encoding="utf-8")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_PATH", tmp_path / "state.sqlite3")
    monkeypatch.setattr(sloth_mode, "DB_PATH", tmp_path / "state.sqlite3")
    return root

def test_sloth_mode_is_disabled_by_default(workspace):
    assert sloth_mode.settings()["enabled"] is False

def test_sloth_mode_review_never_moves_files(workspace):
    before = (workspace / "inbox" / "note.txt").read_bytes()
    sloth_mode.configure({"inbox": "inbox", "enabled": False})
    result = sloth_mode.run_once()
    assert result["files_seen"] == 1
    assert result["files_changed"] == 0
    assert (workspace / "inbox" / "note.txt").read_bytes() == before
    assert (workspace / "inbox" / "note.txt").exists()

def test_sloth_rejects_path_escape(workspace):
    with pytest.raises(ValueError):
        sloth_mode.configure({"inbox": "../outside"})

def test_sloth_schedule_has_safe_bounds(workspace):
    with pytest.raises(ValueError):
        sloth_mode.configure({"interval_minutes": 1})
    with pytest.raises(ValueError):
        sloth_mode.configure({"interval_minutes": 2000})

def test_insights_are_metadata_only(workspace):
    result = insights.workspace_insights(".")
    assert result["files_count"] == 2
    assert result["extension_counts"][".txt"] == 1
    assert "No file content was uploaded" in result["message"]
    assert (workspace / "inbox" / "note.txt").read_text(encoding="utf-8") == "A small note"

def test_path_escape_rejected(workspace):
    with pytest.raises(UnsafePath):
        safe_workspace_path("../outside")

def test_empty_inbox_is_valid_review(workspace):
    (workspace / "inbox" / "note.txt").unlink()
    result = sloth_mode.run_once()
    assert result["files_seen"] == 0
    assert result["files_changed"] == 0
