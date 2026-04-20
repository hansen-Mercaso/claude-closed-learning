from __future__ import annotations

import importlib
import sys
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))


def _load_module():
    return importlib.import_module("hermes_install.uninstall_cli")


def test_uninstall_cli_module_exposes_main_callable():
    mod = _load_module()
    assert callable(mod.main)


def test_main_returns_1_when_target_selection_is_cancelled(monkeypatch):
    mod = _load_module()

    shown_errors: list[tuple[str, str]] = []
    shown_infos: list[tuple[str, str]] = []
    uninstall_calls: list[Path] = []

    monkeypatch.setattr(mod.ui, "choose_target_directory", lambda: None)
    monkeypatch.setattr(mod.ui, "show_error", lambda title, message: shown_errors.append((title, message)))
    monkeypatch.setattr(mod.ui, "show_info", lambda title, message: shown_infos.append((title, message)))

    def fake_uninstall(target_repo: Path) -> dict:
        uninstall_calls.append(target_repo)
        return {"ok": True}

    monkeypatch.setattr(mod, "uninstall_from_target", fake_uninstall)

    assert mod.main() == 1
    assert uninstall_calls == []
    assert shown_infos == []
    assert len(shown_errors) == 1


def test_main_calls_uninstall_and_returns_0_on_success(monkeypatch, tmp_path: Path):
    mod = _load_module()

    shown_errors: list[tuple[str, str]] = []
    shown_infos: list[tuple[str, str]] = []
    uninstall_calls: list[Path] = []

    target = tmp_path / "target-repo"
    target.mkdir()

    monkeypatch.setattr(mod.ui, "choose_target_directory", lambda: str(target))
    monkeypatch.setattr(mod.ui, "show_error", lambda title, message: shown_errors.append((title, message)))
    monkeypatch.setattr(mod.ui, "show_info", lambda title, message: shown_infos.append((title, message)))

    def fake_uninstall(target_repo: Path) -> dict:
        uninstall_calls.append(target_repo)
        return {"ok": True}

    monkeypatch.setattr(mod, "uninstall_from_target", fake_uninstall)

    assert mod.main() == 0
    assert uninstall_calls == [Path(str(target))]
    assert shown_errors == []
    assert len(shown_infos) == 1


def test_main_returns_1_when_uninstall_result_is_not_ok(monkeypatch, tmp_path: Path):
    mod = _load_module()

    shown_errors: list[tuple[str, str]] = []
    shown_infos: list[tuple[str, str]] = []

    target = tmp_path / "target-repo"
    target.mkdir()

    monkeypatch.setattr(mod.ui, "choose_target_directory", lambda: target)
    monkeypatch.setattr(mod.ui, "show_error", lambda title, message: shown_errors.append((title, message)))
    monkeypatch.setattr(mod.ui, "show_info", lambda title, message: shown_infos.append((title, message)))
    monkeypatch.setattr(mod, "uninstall_from_target", lambda target_repo: {"ok": False, "error": "failed"})

    assert mod.main() == 1
    assert len(shown_errors) == 1
    assert shown_infos == []


def test_main_returns_1_when_unexpected_exception_happens(monkeypatch, tmp_path: Path):
    mod = _load_module()

    shown_errors: list[tuple[str, str]] = []
    shown_infos: list[tuple[str, str]] = []

    target = tmp_path / "target-repo"
    target.mkdir()

    monkeypatch.setattr(mod.ui, "choose_target_directory", lambda: target)
    monkeypatch.setattr(mod.ui, "show_error", lambda title, message: shown_errors.append((title, message)))
    monkeypatch.setattr(mod.ui, "show_info", lambda title, message: shown_infos.append((title, message)))

    def fail_uninstall(_: Path) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "uninstall_from_target", fail_uninstall)

    assert mod.main() == 1
    assert len(shown_errors) == 1
    assert shown_infos == []
