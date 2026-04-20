from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from hermes_install.migrator import uninstall_from_target

LEARNING_STOP = "scripts/hermes_learning/hooks/stop-hook.sh"
LEARNING_PRECOMPACT = "FORCE_EXTRACTION=true scripts/hermes_learning/hooks/stop-hook.sh"
LEARNING_SESSION_START = "scripts/hermes_learning/hooks/session-start.sh"


def _collect_command_hooks(settings: dict) -> list[str]:
    commands: list[str] = []
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return commands

    for blocks in hooks.values():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_hooks = block.get("hooks", [])
            if not isinstance(block_hooks, list):
                continue
            for hook in block_hooks:
                if isinstance(hook, dict) and hook.get("type") == "command":
                    command = hook.get("command")
                    if isinstance(command, str):
                        commands.append(command)
    return commands


def test_uninstall_removes_learning_script_and_settings_but_keeps_other_entries(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    learning_dir = target / "scripts" / "hermes_learning"
    (learning_dir / "hooks").mkdir(parents=True)
    (learning_dir / "hooks" / "stop-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "learning": {
                        "command": "python",
                        "args": ["scripts/hermes_learning/mcp/server.py"],
                    },
                    "other": {"command": "node", "args": ["scripts/other.js"]},
                },
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {"type": "command", "command": LEARNING_STOP},
                                {"type": "command", "command": "scripts/keep-stop.sh"},
                            ]
                        }
                    ],
                    "PreCompact": [
                        {
                            "matcher": "manual|auto",
                            "hooks": [
                                {"type": "command", "command": LEARNING_PRECOMPACT},
                                {"type": "command", "command": "scripts/keep-precompact.sh"},
                            ],
                        }
                    ],
                    "SessionStart": [
                        {
                            "hooks": [
                                {"type": "command", "command": LEARNING_SESSION_START},
                                {"type": "command", "command": "scripts/keep-session-start.sh"},
                            ]
                        }
                    ],
                },
                "theme": "dark",
            }
        ),
        encoding="utf-8",
    )

    out = uninstall_from_target(target)

    assert out["ok"] is True
    assert not learning_dir.exists()

    raw = settings_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    updated = json.loads(raw)

    assert updated["theme"] == "dark"
    assert "learning" not in updated["mcpServers"]
    assert updated["mcpServers"]["other"] == {"command": "node", "args": ["scripts/other.js"]}

    commands = _collect_command_hooks(updated)
    assert LEARNING_STOP not in commands
    assert LEARNING_PRECOMPACT not in commands
    assert LEARNING_SESSION_START not in commands
    assert "scripts/keep-stop.sh" in commands
    assert "scripts/keep-precompact.sh" in commands
    assert "scripts/keep-session-start.sh" in commands


def test_uninstall_succeeds_when_settings_file_is_missing(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    learning_dir = target / "scripts" / "hermes_learning"
    learning_dir.mkdir(parents=True)

    out = uninstall_from_target(target)

    assert out["ok"] is True
    assert not learning_dir.exists()
    assert not (target / ".claude" / "settings.json").exists()


def test_uninstall_is_idempotent_when_run_repeatedly(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    learning_dir = target / "scripts" / "hermes_learning"
    learning_dir.mkdir(parents=True)

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "learning": {"command": "python", "args": ["scripts/hermes_learning/mcp/server.py"]},
                    "other": {"command": "node"},
                },
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": LEARNING_STOP}]}],
                },
            }
        ),
        encoding="utf-8",
    )

    first = uninstall_from_target(target)
    second = uninstall_from_target(target)

    assert first["ok"] is True
    assert second["ok"] is True
    assert not learning_dir.exists()

    updated = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "learning" not in updated["mcpServers"]
    assert LEARNING_STOP not in _collect_command_hooks(updated)


def test_uninstall_returns_error_when_target_missing(tmp_path: Path):
    out = uninstall_from_target(tmp_path / "missing")

    assert out["ok"] is False
    assert out["error_code"] == "target_missing"


def test_uninstall_returns_error_when_settings_json_invalid(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{oops", encoding="utf-8")

    out = uninstall_from_target(target)

    assert out["ok"] is False
    assert out["error_code"] == "invalid_settings_json"


def test_uninstall_returns_error_when_settings_json_is_not_object(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps(["x"]), encoding="utf-8")

    out = uninstall_from_target(target)

    assert out["ok"] is False
    assert out["error_code"] == "invalid_settings_json"


def test_uninstall_preserves_empty_hook_event_lists(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"hooks": {"Stop": []}, "mcpServers": {"learning": {"command": "python"}}}),
        encoding="utf-8",
    )

    out = uninstall_from_target(target)

    assert out["ok"] is True
    updated = json.loads(settings_path.read_text(encoding="utf-8"))
    assert updated["hooks"]["Stop"] == []


def test_uninstall_rejects_unsafe_resolved_settings_path(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"mcpServers": {"learning": {"command": "python"}}}), encoding="utf-8")

    outside = tmp_path / "outside-settings.json"
    outside.write_text("{}", encoding="utf-8")

    real_resolve = Path.resolve

    def fake_resolve(self: Path, strict: bool = False):
        if self.as_posix() == settings_path.as_posix():
            return outside
        return real_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    out = uninstall_from_target(target)

    assert out["ok"] is False
    assert out["error_code"] == "unsafe_settings_path"


def test_uninstall_handles_symlinked_learning_path(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    scripts_dir = target / "scripts"
    scripts_dir.mkdir(parents=True)

    real_learning_dir = target / "real-learning"
    real_learning_dir.mkdir()
    (real_learning_dir / "marker.txt").write_text("keep", encoding="utf-8")

    learning_link = scripts_dir / "hermes_learning"
    try:
        learning_link.symlink_to(real_learning_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")

    out = uninstall_from_target(target)

    assert out["ok"] is True
    assert not learning_link.exists()
    assert real_learning_dir.exists()
    assert (real_learning_dir / "marker.txt").read_text(encoding="utf-8") == "keep"


def test_uninstall_returns_structured_error_when_settings_write_fails(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "learning": {
                        "command": "python",
                        "args": ["scripts/hermes_learning/mcp/server.py"],
                    }
                },
                "hooks": {
                    "Stop": [{"hooks": [{"type": "command", "command": LEARNING_STOP}]}]
                },
            }
        ),
        encoding="utf-8",
    )

    original_write_text = Path.write_text

    def fail_settings_write(self: Path, data: str, encoding: str = "utf-8", errors=None, newline=None):
        if self == settings_path.resolve():
            raise OSError("disk full")
        return original_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", fail_settings_write)

    out = uninstall_from_target(target)

    assert out["ok"] is False
    assert out["error_code"] == "settings_write_failed"
    assert out["path"] == settings_path.as_posix()
    assert "disk full" in out["message"]


def test_uninstall_rejects_learning_path_resolved_outside_target(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()

    scripts_dir = target / "scripts"
    scripts_dir.mkdir(parents=True)
    learning_dir = scripts_dir / "hermes_learning"
    learning_dir.mkdir(parents=True)

    outside_learning = tmp_path / "outside-learning"
    outside_learning.mkdir(parents=True)

    real_resolve = Path.resolve

    def fake_resolve(self: Path, strict: bool = False):
        if self == learning_dir:
            return outside_learning
        return real_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    out = uninstall_from_target(target)

    assert out["ok"] is False
    assert out["error_code"] == "unsafe_learning_path"


def test_uninstall_returns_structured_error_when_settings_read_fails(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()

    settings_path = target / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"mcpServers": {"learning": {"command": "python"}}}), encoding="utf-8")

    original_read_text = Path.read_text

    def fail_settings_read(self: Path, encoding: str | None = None, errors: str | None = None):
        if self == settings_path.resolve():
            raise OSError("permission denied")
        return original_read_text(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_settings_read)

    out = uninstall_from_target(target)

    assert out["ok"] is False
    assert out["error_code"] == "settings_read_failed"
    assert out["path"] == settings_path.as_posix()
    assert "permission denied" in out["message"]
