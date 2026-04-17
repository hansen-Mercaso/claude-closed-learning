import json
import os
import shutil
import subprocess
from pathlib import Path


SESSION_START_HOOK = "scripts/hermes_learning/hooks/session-start.sh"


def _bash_executable() -> str:
    candidates = [
        Path(os.environ.get("ProgramW6432", "")) / "Git/bin/bash.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Git/bin/bash.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Git/bin/bash.exe",
    ]
    for candidate in candidates:
        if str(candidate) and candidate.exists():
            return str(candidate)
    return shutil.which("bash") or "bash"


def _run_session_start(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        [_bash_executable(), SESSION_START_HOOK],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=str(Path(__file__).resolve().parents[2]),
        env=merged_env,
    )


def test_session_start_emits_additional_context(tmp_path: Path):
    learning_dir = tmp_path / "learning"
    learning_dir.mkdir()

    (learning_dir / "session-state.json").write_text("{}\n", encoding="utf-8")
    (learning_dir / "candidates.json").write_text(
        json.dumps(
            [
                {
                    "title": "Review approval",
                    "content": "Pending approval item",
                    "status": "pending",
                }
            ]
        ),
        encoding="utf-8",
    )

    cp = _run_session_start({"PROJECT_LEARNING_DIR": str(learning_dir)})

    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    assert "hookSpecificOutput" in payload
    assert "additionalContext" in payload["hookSpecificOutput"]


def test_session_start_emits_additional_context_for_v2_candidates_payload(tmp_path: Path):
    learning_dir = tmp_path / "learning"
    learning_dir.mkdir()

    (learning_dir / "session-state.json").write_text("{}\n", encoding="utf-8")
    (learning_dir / "candidates.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "kind": "candidates",
                "rows": [
                    {
                        "title": "Review approval",
                        "content": "Pending approval item",
                        "status": "pending",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    cp = _run_session_start({"PROJECT_LEARNING_DIR": str(learning_dir)})

    assert cp.returncode == 0
    payload = json.loads(cp.stdout)
    assert "hookSpecificOutput" in payload
    assert "additionalContext" in payload["hookSpecificOutput"]
