from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from hermes_install.migrator import ensure_git_repo, preview_install


def test_ensure_git_repo_auto_inits_non_repo(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    ensure_git_repo(target)

    probe = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0
    assert probe.stdout.strip() == "true"


def test_preview_install_returns_plan_with_settings_change(tmp_path: Path):
    source_root = tmp_path / "template" / "scripts" / "hermes_learning"
    target = tmp_path / "target"
    source_root.mkdir(parents=True)
    (source_root / "migrate.py").write_text("# ok\n", encoding="utf-8")
    target.mkdir()

    ensure_git_repo(target)
    out = preview_install(source_root=source_root, target_repo=target)

    assert out["ok"] is True
    assert "plan" in out
    assert "settings_change" in out["plan"]


def test_ensure_git_repo_is_idempotent(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()

    ensure_git_repo(target)
    ensure_git_repo(target)

    assert (target / ".git").exists()


def test_migrator_can_import_without_scripts_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delitem(sys.modules, "hermes_install.migrator", raising=False)

    original_modules = sys.modules.copy()

    class _Blocked(dict):
        def __contains__(self, key):
            if key == "scripts" or str(key).startswith("scripts."):
                return False
            return super().__contains__(key)

        def __getitem__(self, key):
            if key == "scripts" or str(key).startswith("scripts."):
                raise KeyError(key)
            return super().__getitem__(key)

    blocked = _Blocked(original_modules)
    monkeypatch.setattr(sys, "modules", blocked)

    mod = importlib.import_module("hermes_install.migrator")
    assert callable(mod.ensure_git_repo)
