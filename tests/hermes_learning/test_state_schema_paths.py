from __future__ import annotations

from pathlib import Path

from scripts.hermes_learning.state import (
    SCHEMA_VERSION,
    learning_paths,
    migrate_candidates_payload,
    normalize_project_id,
    storage_root,
)


def test_storage_root_prefers_learning_storage_root(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_STORAGE_ROOT", str(tmp_path / "lr"))
    monkeypatch.setenv("LEARNING_HOME_OVERRIDE", str(tmp_path / "legacy"))
    assert storage_root() == tmp_path / "lr"


def test_normalize_project_id_is_stable():
    pid = normalize_project_id("C:/Workspace/Claude-Hybrid-Learning/")
    assert pid == "c-workspace-claude-hybrid-learning"


def test_learning_paths_include_expected_targets(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_STORAGE_ROOT", str(tmp_path))
    paths = learning_paths("proj-a")
    assert paths["project_candidates"].as_posix().endswith("projects/proj-a/learning/candidates.json")
    assert paths["global_candidates"].as_posix().endswith("learning/global-candidates.json")


def test_migrate_candidates_payload_from_v1_list():
    migrated = migrate_candidates_payload([
        {"id": "c1", "status": "pending", "content": "x"},
    ])
    assert migrated["schema_version"] == SCHEMA_VERSION
    assert migrated["kind"] == "candidates"
    assert migrated["rows"][0]["id"] == "c1"
