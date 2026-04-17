#!/usr/bin/env bash
set -euo pipefail

learning_dir="${PROJECT_LEARNING_DIR:-$HOME/.claude/projects/default/learning}"
state_file="$learning_dir/session-state.json"
cand_file="$learning_dir/candidates.json"

if [[ ! -f "$state_file" || ! -f "$cand_file" ]]; then
  exit 0
fi

export CAND_FILE="$cand_file"
pending_count="$(python - <<'PY'
import json
import os
from pathlib import Path

raw = Path(os.environ["CAND_FILE"]).read_text(encoding="utf-8")
try:
    payload = json.loads(raw or "[]")
except json.JSONDecodeError:
    payload = []

if isinstance(payload, list):
    rows = payload
elif isinstance(payload, dict):
    rows = payload.get("rows")
else:
    rows = []

if not isinstance(rows, list):
    rows = []

print(sum(1 for item in rows if isinstance(item, dict) and item.get("status") == "pending"))
PY
)"

if [[ "$pending_count" == "0" ]]; then
  exit 0
fi

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"You have %s pending learning candidate(s) awaiting approval in candidates.json."}}\n' "$pending_count"
