"""Tests for the Milestone 8 LangGraph daily workflow.

Services are monkeypatched so the test exercises only the graph wiring and
state aggregation — no network calls or DB writes.
"""

import app.graphs.daily_workflow as wf


class _Result:
    """Minimal stand-in for the pipeline *Result dataclasses."""

    def __init__(self, **kw):
        self._kw = kw

    def as_dict(self):
        return self._kw


def test_daily_workflow_runs_all_nodes_in_order(monkeypatch):
    calls: list[str] = []

    def fake_fetch(query=None, limit_per_provider=None):
        calls.append("fetch")
        return ["a", "b", "c"]  # stand-in articles

    def fake_save(db, fetched):
        calls.append("ingest")
        assert fetched == ["a", "b", "c"]  # carried from fetch node
        return _Result(fetched=3, unique=3, saved=3, duplicates=0)

    def fake_embed(db):
        calls.append("embed")
        return _Result(pending=3, embedded=3, failed=0)

    def fake_dedup(db):
        calls.append("dedup")
        return _Result(processed=3, stories_created=2, sources_attached=1)

    # Patch the names as used inside the workflow module.
    monkeypatch.setattr(wf, "fetch_news", fake_fetch)
    monkeypatch.setattr(wf, "save_articles", fake_save)
    monkeypatch.setattr(wf, "embed_pending_articles", fake_embed)
    monkeypatch.setattr(wf, "deduplicate_articles", fake_dedup)
    monkeypatch.setattr(wf, "SessionLocal", lambda: _FakeSession())

    summary = wf.run_daily_workflow(query="ai", limit_per_provider=5)

    assert calls == ["fetch", "ingest", "embed", "dedup"]
    assert summary["fetched"] == 3
    assert summary["ingest"]["saved"] == 3
    assert summary["embed"]["embedded"] == 3
    assert summary["dedup"]["stories_created"] == 2


class _FakeSession:
    def close(self):
        pass


def test_build_daily_graph_compiles():
    app = wf.build_daily_graph()
    # A compiled graph exposes invoke(); node set should match our pipeline.
    assert hasattr(app, "invoke")
    assert {"fetch", "ingest", "embed", "deduplicate"} <= set(app.get_graph().nodes)
