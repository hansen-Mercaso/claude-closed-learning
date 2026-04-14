#!/usr/bin/env bash
set -euo pipefail

learning_dir="${PROJECT_LEARNING_DIR:-$HOME/.claude/projects/default/learning}"
state_file="$learning_dir/session-state.json"
cand_file="$learning_dir/candidates.json"

if [[ ! -f "$state_file" || ! -f "$cand_file" ]]; then
  exit 0
fi

export CAND_FILE="$cand_file"
pending_count="$({ python -c 'import json, os; from pathlib import Path; data = json.loads(Path(os.environ["CAND_FILE"]).read_text(encoding="utf-8") or "[]"); print(sum(1 for item in data if item.get("status") == "pending"))'; } )"

if [[ "$pending_count" == "0" ]]; then
  exit 0
fi

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"You have %s pending learning candidate(s) awaiting approval in candidates.json."}}\n' "$pending_count"
