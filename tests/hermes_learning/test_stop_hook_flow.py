import os
import shutil
import subprocess
from pathlib import Path


STOP_HOOK = "scripts/hermes_learning/hooks/stop-hook.sh"


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


def _run_stop_hook(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        [_bash_executable(), STOP_HOOK],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=str(Path(__file__).resolve().parents[2]),
        env=merged_env,
    )


def test_child_guard_short_circuit(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")

    cp = _run_stop_hook(
        {
            "LEARNING_REVIEW_CHILD": "1",
            "CLAUDE_TRANSCRIPT_PATH": str(transcript),
            "DRY_RUN": "1",
            "FORCE_EXTRACTION": "true",
        }
    )

    assert cp.returncode == 0
    assert cp.stdout == ""
    assert cp.stderr == ""


def test_dry_run_prints_review_command(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")

    cp = _run_stop_hook(
        {
            "CLAUDE_TRANSCRIPT_PATH": str(transcript),
            "DRY_RUN": "1",
        }
    )

    assert cp.returncode == 0
    assert "LEARNING_REVIEW_CHILD=1 claude --print --no-session-persistence" in cp.stderr


def test_force_extraction_uses_review_command(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'LEARNING_REVIEW_CHILD=%s claude %s\\n' \"${LEARNING_REVIEW_CHILD:-}\" \"$*\"\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)

    cp = _run_stop_hook(
        {
            "CLAUDE_TRANSCRIPT_PATH": str(transcript),
            "FORCE_EXTRACTION": "true",
            "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        }
    )

    assert cp.returncode == 0
    assert "LEARNING_REVIEW_CHILD=1 claude --print --no-session-persistence" in cp.stdout
