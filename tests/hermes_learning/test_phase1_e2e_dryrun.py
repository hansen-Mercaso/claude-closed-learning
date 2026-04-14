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


def test_phase1_stop_hook_dry_run_prints_review_command(tmp_path: Path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"remember this"}]}}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_TRANSCRIPT_PATH": str(transcript),
            "FORCE_EXTRACTION": "true",
            "DRY_RUN": "1",
        }
    )

    completed = subprocess.run(
        [_bash_executable(), STOP_HOOK],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=str(Path(__file__).resolve().parents[2]),
        env=env,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert (
        "LEARNING_REVIEW_CHILD=1 claude --print --no-session-persistence"
        in completed.stderr
    )
