from __future__ import annotations

import json
from pathlib import Path

CONF_RANK = {"low": 0, "medium": 1, "high": 2}


class CandidateBuffer:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        txt = self.path.read_text(encoding="utf-8").strip()
        return json.loads(txt) if txt else []

    def _write_all(self, rows: list[dict]) -> None:
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, cand: dict) -> dict:
        rows = self.read_all()
        key = cand.get("dedupe_key")
        if not key:
            rows.append(cand)
            self._write_all(rows)
            return {"action": "append"}

        for i, row in enumerate(rows):
            if row.get("dedupe_key") != key:
                continue
            if row.get("status") in {"approved", "rejected"}:
                return {"action": "skip_decided"}
            old = CONF_RANK.get(row.get("confidence", "low"), 0)
            new = CONF_RANK.get(cand.get("confidence", "low"), 0)
            if new >= old:
                rows[i] = {**row, **cand}
                self._write_all(rows)
                return {"action": "replace"}
            return {"action": "skip_lower_confidence"}

        rows.append(cand)
        self._write_all(rows)
        return {"action": "append"}
