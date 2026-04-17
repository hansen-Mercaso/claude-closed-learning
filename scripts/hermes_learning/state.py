from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path

SCHEMA_VERSION = 2


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return Path(value)


def storage_root() -> Path:
    root = _env_path("LEARNING_STORAGE_ROOT")
    if root is not None:
        return root

    home_override = _env_path("LEARNING_HOME_OVERRIDE")
    if home_override is not None:
        return home_override

    return Path.home() / ".claude"


def normalize_project_id(workspace_path: str) -> str:
    normalized_workspace = unicodedata.normalize("NFKC", workspace_path).replace("\\", "/").strip()
    normalized_workspace = re.sub(r"/+", "/", normalized_workspace)
    if normalized_workspace != "/":
        normalized_workspace = normalized_workspace.rstrip("/")

    slug_source = unicodedata.normalize("NFKD", normalized_workspace.lower())
    ascii_slug = slug_source.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_slug)
    slug = re.sub(r"-+", "-", slug).strip("-")

    short_hash = hashlib.sha256(normalized_workspace.encode("utf-8")).hexdigest()[:10]
    readable_slug = slug or "unknown-project"
    return f"{readable_slug}-{short_hash}"


def learning_paths(project_id: str) -> dict[str, Path]:
    base = storage_root()
    safe_project_id = normalize_project_id(project_id)
    return {
        "project_state": base / "projects" / safe_project_id / "learning" / "session-state.json",
        "project_candidates": base / "projects" / safe_project_id / "learning" / "candidates.json",
        "global_candidates": base / "learning" / "global-candidates.json",
        "proof_events": base / "projects" / safe_project_id / "learning" / "proof-events.jsonl",
        "closure_report": base / "projects" / safe_project_id / "learning" / "closure_proof_report.json",
    }


def migrate_candidates_payload(payload: object) -> dict:
    if isinstance(payload, dict) and payload.get("kind") == "candidates":
        out = dict(payload)
        out["schema_version"] = SCHEMA_VERSION
        rows = out.get("rows")
        out["rows"] = rows if isinstance(rows, list) else []
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
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return default
