#!/usr/bin/env bash
set -euo pipefail

if [[ "${LEARNING_REVIEW_CHILD:-}" == "1" ]]; then
  exit 0
fi

if [[ -z "${CLAUDE_TRANSCRIPT_PATH:-}" || ! -f "${CLAUDE_TRANSCRIPT_PATH}" ]]; then
  exit 0
fi

review='Review the transcript and save durable learnings only when they are specific, reusable, and supported by evidence from this session.'
review_cmd="LEARNING_REVIEW_CHILD=1 claude --print --no-session-persistence --tools \"learning_save,memory_read\" -p \"${review}\" 2>/dev/null"

if [[ "${DRY_RUN:-}" == "1" ]]; then
  printf '%s\n' "$review_cmd" >&2
  exit 0
fi

if [[ "${FORCE_EXTRACTION:-}" == "true" ]]; then
  eval "$review_cmd"
  exit 0
fi

exit 0
