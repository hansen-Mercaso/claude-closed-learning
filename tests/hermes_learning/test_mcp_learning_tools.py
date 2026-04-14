from scripts.hermes_learning.mcp.server import learning_save


def test_global_high_confidence_autowrite(monkeypatch):
    written = {}
    monkeypatch.setattr("scripts.hermes_learning.mcp.server.write_memory", lambda *a, **k: written.setdefault("ok", True))
    monkeypatch.setattr("scripts.hermes_learning.mcp.server.write_skill", lambda *a, **k: written.setdefault("ok", True))

    r = learning_save(
        scope="global", kind="memory", title="t", content="c", evidence="e",
        confidence="high", dedupe_key="k"
    )
    assert r["route"] == "autowrite"


def test_project_or_nonhigh_routes_to_buffer(monkeypatch):
    calls = []
    monkeypatch.setattr("scripts.hermes_learning.mcp.server.buffer_add", lambda c: calls.append(c) or {"action": "append"})

    r = learning_save(
        scope="project", kind="memory", title="t", content="c", evidence="e",
        confidence="high", dedupe_key="k"
    )
    assert r["route"] == "candidate_buffer"


def test_fact_in_phase1_forced_pending(monkeypatch):
    calls = []
    monkeypatch.setattr("scripts.hermes_learning.mcp.server.buffer_add", lambda c: calls.append(c) or {"action": "append"})

    r = learning_save(
        scope="global", kind="fact", title="t", content="c", evidence="e",
        confidence="high", dedupe_key="k"
    )
    assert r["route"] == "candidate_buffer"
    assert calls[0]["kind"] == "fact"
