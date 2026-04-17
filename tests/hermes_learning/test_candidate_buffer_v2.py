from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.hermes_learning.mcp.candidate_buffer import CandidateBuffer
from scripts.hermes_learning.state import SCHEMA_VERSION


def test_add_assigns_id_created_updated_and_writes_schema_payload(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)

    result = b.add({"dedupe_key": "k1", "confidence": "high", "content": "x", "status": "pending"})

    assert result["action"] == "append"
    row = b.read_all()[0]
    assert row["id"].startswith("cand-")
    assert "created_at" in row
    assert "updated_at" in row

    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["kind"] == "candidates"
    assert isinstance(payload["rows"], list)


def test_read_all_migrates_legacy_list_payload_on_write(tmp_path: Path):
    p = tmp_path / "candidates.json"
    p.write_text(
        json.dumps([
            {"id": "c0", "dedupe_key": "k0", "confidence": "medium", "content": "old", "status": "pending"}
        ]),
        encoding="utf-8",
    )

    b = CandidateBuffer(p)
    rows = b.read_all()
    assert len(rows) == 1

    b.add({"dedupe_key": "k1", "confidence": "high", "content": "new", "status": "pending"})
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["kind"] == "candidates"
    assert len(payload["rows"]) == 2


def test_dedupe_equal_confidence_prefers_newer_and_preserves_stable_id(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)

    old = datetime.now(timezone.utc) - timedelta(days=2)
    newer = old + timedelta(days=1)

    b.add(
        {
            "id": "c1",
            "dedupe_key": "k1",
            "confidence": "medium",
            "content": "old",
            "status": "pending",
            "created_at": old.isoformat(),
            "updated_at": old.isoformat(),
        }
    )
    b.add(
        {
            "dedupe_key": "k1",
            "confidence": "medium",
            "content": "new",
            "status": "pending",
            "updated_at": newer.isoformat(),
        }
    )

    row = b.read_all()[0]
    assert row["content"] == "new"
    assert row["id"] == "c1"
    assert row["created_at"] == old.isoformat()


def test_dedupe_equal_confidence_skips_older_candidate(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)

    newer = datetime.now(timezone.utc)
    older = newer - timedelta(days=1)

    b.add(
        {
            "id": "c1",
            "dedupe_key": "k1",
            "confidence": "medium",
            "content": "keep",
            "status": "pending",
            "created_at": older.isoformat(),
            "updated_at": newer.isoformat(),
        }
    )
    result = b.add(
        {
            "dedupe_key": "k1",
            "confidence": "medium",
            "content": "drop",
            "status": "pending",
            "updated_at": older.isoformat(),
        }
    )

    assert result["action"] == "skip_lower_confidence"
    row = b.read_all()[0]
    assert row["content"] == "keep"


def test_update_status_updates_status_and_timestamp(tmp_path: Path):
    p = tmp_path / "candidates.json"
    b = CandidateBuffer(p)

    old = datetime.now(timezone.utc) - timedelta(days=3)
    b.add(
        {
            "id": "c1",
            "dedupe_key": "k1",
            "confidence": "high",
            "content": "x",
            "status": "pending",
            "created_at": old.isoformat(),
            "updated_at": old.isoformat(),
        }
    )

    result = b.update_status("c1", "approved")
    assert result["action"] == "status_updated"

    row = b.read_all()[0]
    assert row["status"] == "approved"
    assert row["updated_at"] != old.isoformat()


def test_list_pending_cap_and_low_filter_and_sorting(tmp_path: Path):
    b = CandidateBuffer(tmp_path / "candidates.json")
    now = datetime.now(timezone.utc)

    b.add(
        {
            "id": "m1",
            "dedupe_key": "m1",
            "confidence": "medium",
            "content": "m1",
            "status": "pending",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": (now - timedelta(days=1)).isoformat(),
        }
    )
    b.add(
        {
            "id": "h1",
            "dedupe_key": "h1",
            "confidence": "high",
            "content": "h1",
            "status": "pending",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": (now - timedelta(hours=2)).isoformat(),
        }
    )
    b.add(
        {
            "id": "h2",
            "dedupe_key": "h2",
            "confidence": "high",
            "content": "h2",
            "status": "pending",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": (now - timedelta(hours=1)).isoformat(),
        }
    )
    b.add(
        {
            "id": "l1",
            "dedupe_key": "l1",
            "confidence": "low",
            "content": "l1",
            "status": "pending",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "updated_at": now.isoformat(),
        }
    )

    rows = b.list_pending(cap=3, include_low=False)
    assert [r["id"] for r in rows] == ["h2", "h1", "m1"]


def test_expire_pending_marks_old_rows_expired(tmp_path: Path):
    b = CandidateBuffer(tmp_path / "candidates.json")
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)

    b.add(
        {
            "id": "old-pending",
            "dedupe_key": "k1",
            "confidence": "high",
            "content": "x",
            "status": "pending",
            "created_at": old.isoformat(),
            "updated_at": old.isoformat(),
        }
    )
    b.add(
        {
            "id": "fresh-pending",
            "dedupe_key": "k2",
            "confidence": "high",
            "content": "y",
            "status": "pending",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    )
    b.add(
        {
            "id": "old-approved",
            "dedupe_key": "k3",
            "confidence": "high",
            "content": "z",
            "status": "approved",
            "created_at": old.isoformat(),
            "updated_at": old.isoformat(),
        }
    )

    out = b.expire_pending(ttl_days=7)

    assert out["expired"] == 1
    statuses = {r["id"]: r["status"] for r in b.read_all()}
    assert statuses["old-pending"] == "expired"
    assert statuses["fresh-pending"] == "pending"
    assert statuses["old-approved"] == "approved"
