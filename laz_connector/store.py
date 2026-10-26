"""Per-user connector state with conservative file permissions."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import string
import threading
from datetime import datetime, timezone


def state_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "LazHelper" / "Connector"
    if __import__("sys").platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LazHelper" / "Connector"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "laz-helper" / "connector"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_pairing_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "-".join("".join(secrets.choice(alphabet) for _ in range(3)) for _ in range(2))


def default_state() -> dict:
    return {"version": 1, "pairing_code": new_pairing_code(), "paired_origins": {}, "grants": [], "scope_mode": "selected_folders", "approval_mode": "ask_every_time", "activity": []}


class StateStore:
    def __init__(self, path: Path | None = None):
        self.directory = path or state_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "connector-state.json"
        self.lock = threading.RLock()
        if not self.path.exists():
            self._write(default_state())
        self._state = self._load()
        if not self._state.get("pairing_code"):
            self._state["pairing_code"] = new_pairing_code()
            self._write(self._state)

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("Unsupported connector state version")
            defaults = default_state()
            for key, value in defaults.items():
                data.setdefault(key, value)
            return data
        except (OSError, ValueError, json.JSONDecodeError):
            broken = self.path.with_suffix(".invalid.json")
            try:
                self.path.replace(broken)
            except OSError:
                pass
            data = default_state()
            self._write(data)
            return data

    def _write(self, data: dict) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        temp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def snapshot(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self._state))

    def update(self, mutator):
        with self.lock:
            mutator(self._state)
            self._write(self._state)
            return json.loads(json.dumps(self._state))

    def add_activity(self, action: str, status: str, detail: str) -> None:
        def change(state):
            state.setdefault("activity", []).append({"id": secrets.token_hex(8), "at": now_iso(), "action": action[:40], "status": status[:24], "detail": detail[:240]})
            state["activity"] = state["activity"][-300:]
        self.update(change)
