from pathlib import Path

from scripts.hermes_learning.mcp.candidate_buffer import CandidateBuffer


def test_dedupe_replaces_when_new_confidence_higher(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)
    b.add({"dedupe_key": "k1", "confidence": "medium", "content": "old", "status": "pending"})
    b.add({"dedupe_key": "k1", "confidence": "high", "content": "new", "status": "pending"})
    rows = b.read_all()
    assert len(rows) == 1
    assert rows[0]["content"] == "new"


def test_dedupe_skips_when_existing_confidence_higher(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)
    b.add({"dedupe_key": "k1", "confidence": "high", "content": "keep", "status": "pending"})
    b.add({"dedupe_key": "k1", "confidence": "low", "content": "drop", "status": "pending"})
    rows = b.read_all()
    assert rows[0]["content"] == "keep"


def test_decided_candidate_not_reopened(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)
    b.add({"dedupe_key": "k1", "confidence": "high", "content": "done", "status": "approved"})
    b.add({"dedupe_key": "k1", "confidence": "high", "content": "again", "status": "pending"})
    rows = b.read_all()
    assert rows[0]["status"] == "approved"
    assert rows[0]["content"] == "done"
