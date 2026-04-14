from __future__ import annotations

import json
import sys
from pathlib import Path


def _text(event: dict) -> str:
    msg = event.get("message") or {}
    content = msg.get("content") or []
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            t = item.get("text")
            if isinstance(t, str):
                parts.append(t)
    return "\n".join(parts).strip()


def main() -> int:
    if len(sys.argv) < 3:
        return 0
    path = Path(sys.argv[1])
    n = int(sys.argv[2])
    if not path.exists():
        print("")
        return 0

    turns: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = row.get("type")
        if t == "user":
            text = _text(row)
            if text:
                turns.append(f"User: {text}")
        elif t == "assistant":
            text = _text(row)
            if text:
                turns.append(f"Assistant: {text}")

    if n > 0:
        turns = turns[-(n * 2):]
    print("\n".join(turns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
