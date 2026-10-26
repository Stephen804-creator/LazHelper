import pytest

from app import organizer, policies, profiles


@pytest.fixture
def memory_db(tmp_path, monkeypatch):
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"t_{abs(hash(tmp_path.name))}")


def test_profile_does_not_grant_permissions(memory_db):
    result = profiles.update_assistant_profile({"profile": "developer"})
    assert result["profile"] == "developer"
    assert result["memory_enabled"] is False
    assert policies.get_policy()["move_files"] is False
    assert policies.get_policy()["run_commands"] is False


def test_memory_is_opt_in_and_scoped(memory_db):
    policies.save_instructions([
        {"scope": "global", "instruction": "Use short explanations."},
        {"scope": "folder", "scope_path": "School", "instruction": "Prefer study examples."},
        {"scope": "task", "scope_path": "analysis", "instruction": "Mention uncertainty."},
    ])
    disabled = profiles.instruction_context("School/notes.pdf", "analysis")
    assert "balanced" not in disabled.lower()  # General profile guidance is used, not saved memory.
    assert "Use short explanations." not in disabled
    profiles.update_assistant_profile({"profile": "study", "memory_enabled": True})
    context = profiles.instruction_context("School/notes.pdf", "analysis")
    assert "study guidance" in context.lower()
    assert "Use short explanations." in context
    assert "Prefer study examples." in context
    assert "Mention uncertainty." in context


def test_memory_folder_matching_does_not_match_similar_prefix(memory_db):
    policies.save_instructions([{"scope": "folder", "scope_path": "School", "instruction": "School-only preference."}])
    profiles.update_assistant_profile({"memory_enabled": True})
    assert "School-only preference." not in profiles.instruction_context("Schoolwork/file.txt", "analysis")
    assert "School-only preference." in profiles.instruction_context("School/file.txt", "analysis")


def test_task_scope_is_validated(memory_db):
    with pytest.raises(ValueError, match="simple task type"):
        policies.save_instructions([{"scope": "task", "scope_path": "invalid task type", "instruction": "unsafe"}])
