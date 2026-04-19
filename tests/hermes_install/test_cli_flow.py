from __future__ import annotations

import importlib
import sys
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from hermes_install import ui


def test_cli_module_exposes_main_callable():
    mod = importlib.import_module("hermes_install.cli")
    assert callable(mod.main)


def test_preview_summary_includes_conflict_and_settings_status():
    plan = {
        "file_changes": [
            {"type": "add", "rel": "hooks/stop-hook.sh"},
            {"type": "conflict", "rel": "mcp/server.py"},
            {"type": "skip", "rel": "state.py"},
        ],
        "settings_change": {"changed": True},
    }

    text = ui.build_preview_summary(plan)

    assert "新增: 1" in text
    assert "冲突: 1" in text
    assert "跳过: 1" in text
    assert "settings 变更: 是" in text


class _FakeUI:
    def __init__(self, target: Path, confirmed: bool):
        self.target = target
        self.confirmed = confirmed
        self.messages = []

    def choose_target_directory(self):
        return self.target

    def build_preview_summary(self, plan: dict) -> str:
        return f"preview:{len(plan.get('file_changes', []))}"

    def confirm_preview(self, summary: str) -> bool:
        self.messages.append(summary)
        return self.confirmed

    def show_info(self, title: str, message: str) -> None:
        self.messages.append(f"INFO:{title}:{message}")

    def show_error(self, title: str, message: str) -> None:
        self.messages.append(f"ERROR:{title}:{message}")


def test_main_applies_when_user_confirms(tmp_path: Path, monkeypatch):
    template_root = tmp_path / "template" / "scripts" / "hermes_learning"
    (template_root / "hooks").mkdir(parents=True)
    (template_root / "hooks" / "stop-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (template_root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    target = tmp_path / "target"
    fake_ui = _FakeUI(target=target, confirmed=True)

    import hermes_install.cli as cli

    monkeypatch.setattr(cli, "resolve_template_source", lambda: template_root)
    monkeypatch.setattr(cli, "ui", fake_ui)

    rc = cli.main()

    if rc != 0:
        assert fake_ui.messages, "expected at least one UI message on failure"
        assert any(msg.startswith("ERROR:") for msg in fake_ui.messages), fake_ui.messages

    assert rc == 0
    assert (target / ".claude" / "settings.json").exists()


def test_main_returns_nonzero_when_user_cancels(tmp_path: Path, monkeypatch):
    template_root = tmp_path / "template" / "scripts" / "hermes_learning"
    (template_root / "hooks").mkdir(parents=True)
    (template_root / "hooks" / "stop-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (template_root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    target = tmp_path / "target"
    fake_ui = _FakeUI(target=target, confirmed=False)

    import hermes_install.cli as cli

    monkeypatch.setattr(cli, "resolve_template_source", lambda: template_root)
    monkeypatch.setattr(cli, "ui", fake_ui)

    rc = cli.main()

    assert rc == 1
    assert not (target / ".claude" / "settings.json").exists()
