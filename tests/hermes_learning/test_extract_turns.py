import json
import subprocess
from pathlib import Path


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def test_extract_last_two_turns(tmp_path: Path):
    transcript = tmp_path / "t.jsonl"
    rows = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "u1"}]}}
        ,{"type": "assistant", "message": {"content": [{"type": "text", "text": "a1"}]}}
        ,{"type": "user", "message": {"content": [{"type": "text", "text": "u2"}]}}
        ,{"type": "assistant", "message": {"content": [{"type": "text", "text": "a2"}]}}
        ,{"type": "tool_use"}
    ]
    write_jsonl(transcript, rows)

    out = subprocess.check_output([
        "python", "scripts/hermes_learning/extract_turns.py", str(transcript), "2"
    ], text=True, cwd="c:/workspace/claude-hybrid-learning/.worktrees/hermes-learning")

    assert "User: u1" in out
    assert "Assistant: a1" in out
    assert "User: u2" in out
    assert "Assistant: a2" in out
    assert "tool_use" not in out


def test_missing_file_returns_empty(tmp_path: Path):
    missing = tmp_path / "missing.jsonl"
    out = subprocess.check_output([
        "python", "scripts/hermes_learning/extract_turns.py", str(missing), "3"
    ], text=True, cwd="c:/workspace/claude-hybrid-learning/.worktrees/hermes-learning")
    assert out.strip() == ""
