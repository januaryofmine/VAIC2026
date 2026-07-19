"""Unit tests for the retrieval-api tracing helper."""

from datetime import datetime, timezone

import app.services.tracing as tracing


def teardown_function():
    # keep the module-global thread list clean between tests
    tracing.flush(timeout=2)
    with tracing._lock:
        tracing._threads.clear()


def test_disabled_is_noop(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    now = datetime.now(timezone.utc)
    # must not raise and must not spawn any sender
    tracing.trace_retrieval(
        trace_id=None, name="retrieval", question="q", n_results=0, start=now, end=now
    )
    assert tracing._threads == []


def test_send_async_prunes_finished_threads(monkeypatch):
    # make the POST an instant no-op so worker threads finish immediately
    monkeypatch.setattr(tracing, "_post", lambda events: None)

    # spawn a batch and let them all finish WITHOUT calling flush() (flush would clear
    # the list — we are testing the server path where flush() is never called).
    for _ in range(6):
        tracing._send_async([{}])
    for t in list(tracing._threads):
        t.join(timeout=2)

    # the 6 threads are now dead but still referenced; the next spawn must prune them.
    tracing._send_async([{}])
    assert len(tracing._threads) <= 2  # pruned dead ones, not accumulated all 7
