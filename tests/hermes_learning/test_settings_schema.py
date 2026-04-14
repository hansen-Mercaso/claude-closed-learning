import json
from pathlib import Path

import pytest

from scripts.hermes_learning.skill_index import build_index


REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = REPO_ROOT / ".claude" / "settings.json"


def _load_settings() -> dict:
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def _first_command(settings: dict, event: str) -> str:
    return settings["hooks"][event][0]["hooks"][0]["command"]


def test_learning_mcp_and_hooks_are_configured():
    settings = _load_settings()
    worktree_root = str(REPO_ROOT).replace("\\", "/")

    learning = settings["mcpServers"]["learning"]
    assert learning["command"] == "python"
    assert learning["args"] == [
        f"{worktree_root}/scripts/hermes_learning/mcp/server.py"
    ]

    assert "Stop" in settings["hooks"]
    assert "PreCompact" in settings["hooks"]
    assert "SessionStart" in settings["hooks"]

    assert _first_command(settings, "Stop") == (
        f"{worktree_root}/scripts/hermes_learning/hooks/stop-hook.sh"
    )
    assert _first_command(settings, "PreCompact") == (
        "FORCE_EXTRACTION=true "
        f"{worktree_root}/scripts/hermes_learning/hooks/stop-hook.sh"
    )
    assert _first_command(settings, "SessionStart") == (
        f"{worktree_root}/scripts/hermes_learning/hooks/session-start.sh"
    )


@pytest.mark.parametrize(
    ("relative_dir", "description", "expected_name"),
    [
        ("alpha", "Alpha skill", "alpha"),
        ("nested/beta", "Beta skill", "nested/beta"),
    ],
)
def test_build_index_collects_skill_names_and_descriptions(
    tmp_path: Path, relative_dir: str, description: str, expected_name: str
):
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / relative_dir
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: {description}\n---\n",
        encoding="utf-8",
    )

    out_file = tmp_path / "skill-index.txt"
    build_index(skills_root, out_file)

    assert out_file.read_text(encoding="utf-8").splitlines() == [
        f"- {expected_name}: {description}"
    ]
