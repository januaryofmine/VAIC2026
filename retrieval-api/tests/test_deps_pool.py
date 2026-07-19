"""Unit tests for the pooled DB dependency (get_db) — no real DB required.

The whole point of the pool: pay the (cross-region, expensive) connection handshake
ONCE at startup, then reuse warm connections per request instead of reconnecting.
"""

from contextlib import contextmanager

import app.deps as deps


class _FakeConn:
    pass


class _FakePool:
    """Stand-in for psycopg_pool.ConnectionPool that records how it is used."""

    instances = 0

    # init_pool passes check=ConnectionPool.check_connection; the fake needs the attr.
    check_connection = staticmethod(lambda conn: None)

    def __init__(self, conninfo=None, **kwargs):
        type(self).instances += 1
        self.conninfo = conninfo
        self.kwargs = kwargs
        self.opened = False
        self.closed = False
        self._conn = _FakeConn()

    def open(self, *args, **kwargs):
        self.opened = True

    @contextmanager
    def connection(self):
        yield self._conn

    def close(self):
        self.closed = True


def _reset(monkeypatch):
    monkeypatch.setattr(deps, "_pool", None)
    _FakePool.instances = 0
    monkeypatch.setattr(deps, "ConnectionPool", _FakePool)


def test_configure_registers_vector(monkeypatch):
    called = []
    monkeypatch.setattr(deps, "register_vector", called.append)
    conn = _FakeConn()
    deps._configure(conn)
    assert called == [conn]


def test_init_pool_idempotent(monkeypatch):
    _reset(monkeypatch)
    deps.init_pool()
    deps.init_pool()
    assert _FakePool.instances == 1  # second call is a no-op, not a new pool
    assert deps._pool.opened is True
    deps.close_pool()


def test_get_db_checks_out_from_pool(monkeypatch):
    _reset(monkeypatch)

    def _boom(*args, **kwargs):
        raise AssertionError("get_db must reuse the pool, not psycopg.connect per request")

    monkeypatch.setattr(deps.psycopg, "connect", _boom)

    gen = deps.get_db()
    conn = next(gen)
    assert isinstance(conn, _FakeConn)  # came from the pool
    assert _FakePool.instances == 1  # lazily opened exactly one pool
    gen.close()
    deps.close_pool()


def test_close_pool_resets(monkeypatch):
    _reset(monkeypatch)
    deps.init_pool()
    pool = deps._pool
    deps.close_pool()
    assert pool.closed is True
    assert deps._pool is None
