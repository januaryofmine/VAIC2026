from app.services.reformulation import reformulate_query


def test_passthrough_when_provider_none():
    assert reformulate_query("câu hỏi gốc", model="m", provider="none") == "câu hỏi gốc"


def test_passthrough_when_anthropic_but_no_key():
    assert (
        reformulate_query("câu hỏi gốc", model="m", provider="anthropic", anthropic_api_key="")
        == "câu hỏi gốc"
    )


def test_anthropic_branch_rewrites(monkeypatch):
    class _Messages:
        def create(self, **kwargs):
            block = type("Block", (), {"text": "  truy vấn viết lại  "})()
            return type("Resp", (), {"content": [block]})()

    class _Client:
        def __init__(self, **kwargs):
            self.messages = _Messages()

    monkeypatch.setattr("anthropic.Anthropic", _Client)
    out = reformulate_query("gốc", model="m", provider="anthropic", anthropic_api_key="key")
    assert out == "truy vấn viết lại"  # trimmed


def test_conversational_output_falls_back_to_question(monkeypatch):
    class _Messages:
        def create(self, **kwargs):
            block = type(
                "B", (), {"text": "Tôi cần thêm thông tin.\n\n(Bạn cung cấp tên văn bản?)"}
            )()
            return type("Resp", (), {"content": [block]})()

    class _Client:
        def __init__(self, **kwargs):
            self.messages = _Messages()

    monkeypatch.setattr("anthropic.Anthropic", _Client)
    out = reformulate_query("gốc", model="m", provider="anthropic", anthropic_api_key="k")
    assert out == "gốc"  # multi-line / clarifying answer rejected


def test_overlong_output_falls_back_to_question(monkeypatch):
    class _Messages:
        def create(self, **kwargs):
            return type("Resp", (), {"content": [type("B", (), {"text": "x" * 200})()]})()

    class _Client:
        def __init__(self, **kwargs):
            self.messages = _Messages()

    monkeypatch.setattr("anthropic.Anthropic", _Client)
    assert reformulate_query("gốc", model="m", provider="anthropic", anthropic_api_key="k") == "gốc"


def test_anthropic_failure_falls_back_to_question(monkeypatch):
    class _Boom:
        def __init__(self, **kwargs):
            raise RuntimeError("api down")

    monkeypatch.setattr("anthropic.Anthropic", _Boom)
    out = reformulate_query("gốc", model="m", provider="anthropic", anthropic_api_key="key")
    assert out == "gốc"
