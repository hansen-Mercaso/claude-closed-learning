from __future__ import annotations

import json
import os
import re
from pathlib import Path

SCHEMA_VERSION = 2


def storage_root() -> Path:
    if "LEARNING_STORAGE_ROOT" in os.environ:
        return Path(os.environ["LEARNING_STORAGE_ROOT"])
    if "LEARNING_HOME_OVERRIDE" in os.environ:
        return Path(os.environ["LEARNING_HOME_OVERRIDE"])
    return Path.home() / ".claude"


def normalize_project_id(workspace_path: str) -> str:
    normalized = workspace_path.replace("\\", "/").strip().rstrip("/").lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "unknown-project"


def learning_paths(project_id: str) -> dict[str, Path]:
    base = storage_root()
    return {
        "project_state": base / "projects" / project_id / "learning" / "session-state.json",
        "project_candidates": base / "projects" / project_id / "learning" / "candidates.json",
        "global_candidates": base / "learning" / "global-candidates.json",
        "proof_events": base / "projects" / project_id / "learning" / "proof-events.jsonl",
        "closure_report": base / "projects" / project_id / "learning" / "closure_proof_report.json",
    }


def migrate_candidates_payload(payload: object) -> dict:
    if isinstance(payload, dict) and payload.get("kind") == "candidates":
        out = dict(payload)
        out.setdefault("schema_version", SCHEMA_VERSION)
        out.setdefault("rows", [])
        return out

    if isinstance(payload, list):
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "candidates",
            "rows": payload,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "candidates",
        "rows": [],
    }


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default
