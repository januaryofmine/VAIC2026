"""AI monitoring cho retrieval-api — gửi span truy xuất lên Langfuse.

Vì sao: tiêu chí "Grounding & độ tin cậy" và lộ trình pilot ở UBND cần *đo được*
khâu RAG, không chỉ khâu LLM. Span ở đây cho biết truy xuất mất bao lâu, tầng 1
trả về bao nhiêu ứng viên, reranker có bật không và cuối cùng còn mấy chunk —
đủ để truy nguyên khi một câu trả lời trích dẫn sai.

Thiết kế (khớp paperless-ui/server/utils/llm-trace.ts):
- Zero dependency: chỉ dùng stdlib (urllib) — không thêm gói vào image.
- No-op khi thiếu LANGFUSE_* → đồng đội/CI chạy bình thường.
- Fire-and-forget trong thread nền → không cộng latency vào request.
- Nuốt lỗi, nhưng LANGFUSE_DEBUG=1 sẽ in ra: im lặng tuyệt đối làm lỗi vô hình.
- Nhận `trace_id` từ UI (header X-Trace-Id) để 1 câu hỏi = 1 trace xuyên suốt
  UI → RAG → LLM thay vì hai trace rời rạc.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import urllib.request
import uuid
from datetime import datetime, timezone

_threads: list[threading.Thread] = []
_lock = threading.Lock()


def _cfg() -> dict | None:
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sk = os.environ.get("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        return None
    return {
        "pk": pk,
        "sk": sk,
        "base": os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
    }


def is_enabled() -> bool:
    return _cfg() is not None


def new_trace_id() -> str:
    return str(uuid.uuid4())


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _post(events: list[dict]) -> None:
    cfg = _cfg()
    if not cfg or not events:
        return
    debug = bool(os.environ.get("LANGFUSE_DEBUG"))
    try:
        auth = base64.b64encode(f"{cfg['pk']}:{cfg['sk']}".encode()).decode()
        req = urllib.request.Request(
            f"{cfg['base']}/api/public/ingestion",
            data=json.dumps({"batch": events}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            if debug:
                print(f"[tracing] ingestion HTTP {res.status}: {res.read()[:300]!r}", flush=True)
    except Exception as e:  # noqa: BLE001 — telemetry không được phá luồng chính
        if debug:
            print(f"[tracing] ingestion failed: {e}", flush=True)


def _send_async(events: list[dict]) -> None:
    t = threading.Thread(target=_post, args=(events,), daemon=True)
    with _lock:
        # Dọn thread đã xong để list không phình vô hạn trên server dài hạn (HF Space):
        # flush() chỉ được gọi ở script/test ngắn hạn, KHÔNG bao giờ ở đường request.
        _threads[:] = [x for x in _threads if x.is_alive()]
        _threads.append(t)
    t.start()


def flush(timeout: float = 10.0) -> None:
    """Chờ các span đang bay gửi xong (dùng ở test/script ngắn hạn)."""
    with _lock:
        pending = list(_threads)
        _threads.clear()
    for t in pending:
        t.join(timeout=timeout)


def trace_retrieval(
    *,
    trace_id: str | None,
    name: str,
    question: str,
    n_results: int,
    start: datetime,
    end: datetime,
    metadata: dict | None = None,
    output: object | None = None,
) -> None:
    """Ghi 1 span truy xuất. An toàn khi tắt tracing (return ngay)."""
    if not is_enabled():
        return
    tid = trace_id or new_trace_id()
    now = _iso(datetime.now(timezone.utc))
    latency_ms = int((end - start).total_seconds() * 1000)

    events = [
        # Tạo trace nếu chưa có (idempotent theo id) để span có chỗ neo.
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": now,
            "body": {
                "id": tid,
                "name": "qa-pipeline",
                "timestamp": _iso(start),
                "input": question,
                "tags": ["paperless-meetings", "retrieval-api"],
            },
        },
        {
            "id": str(uuid.uuid4()),
            "type": "span-create",
            "timestamp": now,
            "body": {
                "id": str(uuid.uuid4()),
                "traceId": tid,
                "name": name,
                "startTime": _iso(start),
                "endTime": _iso(end),
                "input": question,
                "output": output,
                "metadata": {**(metadata or {}), "latencyMs": latency_ms, "nResults": n_results},
            },
        },
    ]
    _send_async(events)
