# scripts/hermes_learning/mcp/server.py
from __future__ import annotations

from pathlib import Path
from scripts.hermes_learning.mcp.candidate_buffer import CandidateBuffer
from scripts.hermes_learning.mcp.memory_tool import write_memory
from scripts.hermes_learning.mcp.skills_tool import write_skill


def memory_read() -> dict:
    p = Path.home() / ".claude" / "memory" / "MEMORY.md"
    if not p.exists():
        return {"content": ""}
    return {"content": p.read_text(encoding="utf-8")}


def _global_buffer() -> CandidateBuffer:
    return CandidateBuffer(Path.home() / ".claude" / "learning" / "global-candidates.json")


def buffer_add(cand: dict) -> dict:
    return _global_buffer().add(cand)


def learning_save(scope: str, kind: str, title: str, content: str, evidence: str, confidence: str, dedupe_key: str) -> dict:
    cand = {
        "scope": scope,
        "kind": kind,
        "title": title,
        "content": content,
        "evidence": evidence,
        "confidence": confidence,
        "dedupe_key": dedupe_key,
        "status": "pending",
    }

    # Phase 1 fact fallback: always pending
    if kind == "fact":
        buffer_add(cand)
        return {"route": "candidate_buffer", "reason": "phase1_fact_fallback"}

    if scope == "global" and confidence == "high":
        if kind == "memory":
            write_memory(content=content)
            return {"route": "autowrite", "target": "memory"}
        if kind == "skill":
            write_skill(content=content)
            return {"route": "autowrite", "target": "skill"}

    buffer_add(cand)
    return {"route": "candidate_buffer", "reason": "approval_required_or_low_confidence"}
