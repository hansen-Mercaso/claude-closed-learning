from __future__ import annotations

import re
from pathlib import Path

from scripts.hermes_learning.state import (
    SCHEMA_VERSION,
    learning_paths,
    migrate_candidates_payload,
    normalize_project_id,
    read_json,
    storage_root,
)


def test_storage_root_prefers_learning_storage_root(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_STORAGE_ROOT", str(tmp_path / "lr"))
    monkeypatch.setenv("LEARNING_HOME_OVERRIDE", str(tmp_path / "legacy"))
    assert storage_root() == tmp_path / "lr"


def test_storage_root_empty_storage_root_falls_back_to_home_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_STORAGE_ROOT", "   ")
    monkeypatch.setenv("LEARNING_HOME_OVERRIDE", str(tmp_path / "legacy"))
    assert storage_root() == tmp_path / "legacy"


def test_normalize_project_id_is_stable_and_safe():
    workspace = "C:/Workspace/Claude-Hybrid-Learning/"
    pid = normalize_project_id(workspace)
    assert pid == normalize_project_id(workspace)

    prefix, short_hash = pid.rsplit("-", 1)
    assert prefix == "c-workspace-claude-hybrid-learning"
    assert re.fullmatch(r"[0-9a-f]{10}", short_hash)
    assert re.fullmatch(r"[a-z0-9-]+", pid)


def test_learning_paths_include_expected_targets(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LEARNING_STORAGE_ROOT", str(tmp_path))
    project_id = normalize_project_id("proj-a")
    paths = learning_paths("proj-a")
    assert paths["project_candidates"].as_posix().endswith(
        f"projects/{project_id}/learning/candidates.json"
    )
    assert paths["global_candidates"].as_posix().endswith("learning/global-candidates.json")


def test_migrate_candidates_payload_from_v1_list():
    migrated = migrate_candidates_payload([
        {"id": "c1", "status": "pending", "content": "x"},
    ])
    assert migrated["schema_version"] == SCHEMA_VERSION
    assert migrated["kind"] == "candidates"
    assert migrated["rows"][0]["id"] == "c1"


def test_migrate_candidates_payload_dict_old_schema_normalized_to_current():
    migrated = migrate_candidates_payload(
        {
            "schema_version": 1,
            "kind": "candidates",
            "rows": [{"id": "c1"}],
        }
    )
    assert migrated["schema_version"] == SCHEMA_VERSION


def test_migrate_candidates_payload_dict_non_list_rows_coerced_to_empty_list():
    migrated = migrate_candidates_payload(
        {
            "schema_version": 1,
            "kind": "candidates",
            "rows": {"id": "not-a-list"},
        }
    )
    assert migrated["schema_version"] == SCHEMA_VERSION
    assert migrated["rows"] == []


def test_normalize_project_id_non_ascii_paths_are_distinct():
    first = normalize_project_id("/工作区/项目")
    second = normalize_project_id("/作工作区/项目")

    assert first != second
    assert re.fullmatch(r"[a-z0-9-]+", first)
    assert re.fullmatch(r"[a-z0-9-]+", second)


def test_read_json_missing_invalid_json_and_invalid_utf8_return_default(tmp_path: Path):
    default = {"fallback": True}

    missing = tmp_path / "missing.json"
    assert read_json(missing, default) is default

    broken = tmp_path / "broken.json"
    broken.write_text("{not-valid-json", encoding="utf-8")
    assert read_json(broken, default) is default

    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff\xfe\xfd")
    assert read_json(invalid_utf8, default) is default
