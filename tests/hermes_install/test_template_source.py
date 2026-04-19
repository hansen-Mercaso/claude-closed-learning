from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from hermes_install import template_source
from hermes_install.template_source import pick_latest_stable_tag


def test_pick_latest_stable_tag_prefers_highest_semver():
    tags = ["v0.1.0", "v0.2.0", "v0.10.0", "v0.10.0-rc.1", "not-a-version"]
    assert pick_latest_stable_tag(tags) == "v0.10.0"


def test_pick_latest_stable_tag_raises_when_no_stable_tags():
    tags = ["v0.2.0-rc.1", "snapshot", "foo"]
    with pytest.raises(ValueError, match="no stable semver tag"):
        pick_latest_stable_tag(tags)


def test_extract_template_payload_returns_hermes_learning_root(tmp_path: Path):
    bundle = tmp_path / "bundle"
    root = bundle / "repo-v0.1.0" / "scripts" / "hermes_learning"
    root.mkdir(parents=True)
    (root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    out = template_source.extract_template_payload(bundle / "repo-v0.1.0")

    assert out == root
    assert (out / "migrate.py").exists()


def test_latest_tag_selection_ignores_prerelease_suffixes():
    tags = ["v1.0.0-rc.1", "v1.0.0", "v0.9.9"]
    assert template_source.pick_latest_stable_tag(tags) == "v1.0.0"


def test_list_remote_tags_uses_git_ls_remote(monkeypatch):
    def _fake_run(cmd, capture_output, text, check):
        assert cmd[:3] == ["git", "ls-remote", "--tags"]
        assert template_source.TEMPLATE_REPO in cmd

        class _Res:
            returncode = 0
            stdout = """\
111\trefs/tags/v1.2.0
222\trefs/tags/v1.2.0^{}
333\trefs/tags/v1.1.9
"""
            stderr = ""

        return _Res()

    monkeypatch.setattr(template_source.subprocess, "run", _fake_run)

    tags = template_source.list_remote_tags()

    assert tags == ["v1.2.0", "v1.1.9"]


def test_resolve_template_source_clones_latest_stable_tag(tmp_path: Path, monkeypatch):
    clone_root = tmp_path / "clone"
    hermes_root = clone_root / "scripts" / "hermes_learning"
    hermes_root.mkdir(parents=True)
    (hermes_root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    monkeypatch.setattr(template_source, "list_remote_tags", lambda: ["v1.2.0-rc.1", "v1.2.0"])

    def _fake_clone(repo: str, tag: str, dst: Path):
        assert repo == template_source.TEMPLATE_REPO
        assert tag == "v1.2.0"
        assert dst == clone_root

    monkeypatch.setattr(template_source, "_clone_tag_snapshot", _fake_clone)
    monkeypatch.setattr(template_source.tempfile, "mkdtemp", lambda prefix: str(clone_root))

    resolved = template_source.resolve_template_source()

    assert resolved == clone_root / "scripts" / "hermes_learning"
    assert (resolved / "migrate.py").exists()
