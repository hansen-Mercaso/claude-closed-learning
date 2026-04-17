from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.hermes_learning.state import SCHEMA_VERSION, migrate_candidates_payload

CONF_RANK = {"low": 0, "medium": 1, "high": 2}
TERMINAL_STATUSES = {"approved", "rejected", "applied", "expired"}


class CandidateBuffer:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _parse_dt(self, value: object) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _load_payload(self) -> dict:
        if not self.path.exists():
            return migrate_candidates_payload([])

        txt = self.path.read_text(encoding="utf-8").strip()
        if not txt:
            return migrate_candidates_payload([])

        try:
            payload = json.loads(txt)
        except json.JSONDecodeError:
            payload = []

        return migrate_candidates_payload(payload)

    def _write_payload(self, payload: dict) -> None:
        out = migrate_candidates_payload(payload)
        out["schema_version"] = SCHEMA_VERSION
        out["kind"] = "candidates"
        self.path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    def read_all(self) -> list[dict]:
        payload = self._load_payload()
        rows = payload.get("rows")
        return rows if isinstance(rows, list) else []

    def _write_all(self, rows: list[dict]) -> None:
        self._write_payload({"schema_version": SCHEMA_VERSION, "kind": "candidates", "rows": rows})

    def _candidate_updated_at(self, cand: dict, now: str) -> str:
        updated = cand.get("updated_at")
        if isinstance(updated, str) and updated.strip():
            return updated
        return now

    def add(self, cand: dict) -> dict:
        rows = self.read_all()
        now = self._now()
        incoming = dict(cand)
        incoming.setdefault("id", f"cand-{uuid.uuid4().hex[:8]}")
        incoming.setdefault("created_at", now)
        incoming["updated_at"] = self._candidate_updated_at(incoming, now)

        key = incoming.get("dedupe_key")
        if not key:
            rows.append(incoming)
            self._write_all(rows)
            return {"action": "append", "candidate_id": incoming["id"]}

        for i, row in enumerate(rows):
            if row.get("dedupe_key") != key:
                continue

            if row.get("status") in TERMINAL_STATUSES:
                return {"action": "skip_decided", "candidate_id": row.get("id")}

            old_conf = CONF_RANK.get(row.get("confidence", "low"), 0)
            new_conf = CONF_RANK.get(incoming.get("confidence", "low"), 0)

            old_dt = self._parse_dt(row.get("updated_at") or row.get("created_at"))
            new_dt = self._parse_dt(incoming.get("updated_at") or incoming.get("created_at"))
            newer_or_equal = (
                (old_dt is not None and new_dt is not None and new_dt >= old_dt)
                or (old_dt is None and new_dt is not None)
                or (old_dt is None and new_dt is None)
            )

            if new_conf > old_conf or (new_conf == old_conf and newer_or_equal):
                merged = {**row, **incoming}
                merged["id"] = row.get("id") or incoming["id"]
                merged["created_at"] = row.get("created_at") or incoming["created_at"]
                rows[i] = merged
                self._write_all(rows)
                return {"action": "replace", "candidate_id": merged.get("id")}

            return {"action": "skip_lower_confidence", "candidate_id": row.get("id")}

        rows.append(incoming)
        self._write_all(rows)
        return {"action": "append", "candidate_id": incoming["id"]}

    def update_status(self, candidate_id: str, status: str) -> dict:
        rows = self.read_all()
        for i, row in enumerate(rows):
            if row.get("id") != candidate_id:
                continue
            rows[i] = {**row, "status": status, "updated_at": self._now()}
            self._write_all(rows)
            return {"action": "status_updated", "candidate_id": candidate_id}
        return {"action": "not_found", "candidate_id": candidate_id}

    def list_pending(self, cap: int = 8, include_low: bool = False) -> list[dict]:
        rows = [r for r in self.read_all() if r.get("status") == "pending"]
        if not include_low:
            rows = [r for r in rows if CONF_RANK.get(r.get("confidence", "low"), 0) > 0]

        def sort_key(row: dict) -> tuple[int, float]:
            rank = CONF_RANK.get(row.get("confidence", "low"), 0)
            dt = self._parse_dt(row.get("updated_at") or row.get("created_at"))
            ts = dt.timestamp() if dt is not None else float("-inf")
            return rank, ts

        rows.sort(key=sort_key, reverse=True)
        return rows[:cap]

    def expire_pending(self, ttl_days: int) -> dict:
        rows = self.read_all()
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        now = self._now()
        expired = 0

        for i, row in enumerate(rows):
            if row.get("status") != "pending":
                continue
            dt = self._parse_dt(row.get("updated_at") or row.get("created_at"))
            if dt is None or dt >= cutoff:
                continue
            rows[i] = {**row, "status": "expired", "updated_at": now}
            expired += 1

        if expired:
            self._write_all(rows)

        return {"expired": expired}
