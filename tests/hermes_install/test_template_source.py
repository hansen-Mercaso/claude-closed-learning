from __future__ import annotations

import json
import shutil
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


def test_list_remote_tags_reads_names_from_github_payload(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            payload = [
                {"name": "v1.2.0"},
                {"name": " v1.1.9 "},
                {"not_name": "ignored"},
                "ignored",
            ]
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(template_source.urllib.request, "urlopen", lambda *args, **kwargs: _Resp())

    tags = template_source.list_remote_tags("https://example.invalid/tags")

    assert tags == ["v1.2.0", "v1.1.9", ""]


def test_resolve_template_source_fetches_latest_stable_archive(tmp_path: Path, monkeypatch):
    template_source_root = tmp_path / "repo-v1.2.0" / "scripts" / "hermes_learning"
    template_source_root.mkdir(parents=True)
    (template_source_root / "migrate.py").write_text("# ok\n", encoding="utf-8")

    archive_source_dir = tmp_path / "archive-source"
    archive_source_dir.mkdir()
    shutil.make_archive(
        str(archive_source_dir / "v1.2.0"),
        "zip",
        root_dir=tmp_path,
        base_dir="repo-v1.2.0",
    )
    source_archive = archive_source_dir / "v1.2.0.zip"

    monkeypatch.setattr(template_source, "list_remote_tags", lambda repo_api_tags_url=None: ["v1.2.0-rc.1", "v1.2.0"])
    monkeypatch.setattr(template_source.tempfile, "mkdtemp", lambda prefix: str(tmp_path / "work"))

    def _fake_urlretrieve(url: str, filename: str | Path):
        assert url == f"{template_source.TEMPLATE_REPO}/archive/refs/tags/v1.2.0.zip"
        shutil.copyfile(source_archive, filename)
        return str(filename), None

    monkeypatch.setattr(template_source.urllib.request, "urlretrieve", _fake_urlretrieve)

    resolved = template_source.resolve_template_source()

    assert resolved == tmp_path / "work" / "extract" / "repo-v1.2.0" / "scripts" / "hermes_learning"
    assert (resolved / "migrate.py").exists()
