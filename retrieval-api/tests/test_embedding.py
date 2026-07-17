import numpy as np

import app.services.embedding as emb


def test_embed_query_applies_query_prefix_and_dim(monkeypatch):
    captured = {}

    class FakeModel:
        def encode(self, texts, **kwargs):
            captured["texts"] = texts
            return np.zeros((len(texts), 1024))

    monkeypatch.setattr(emb, "_model", FakeModel())  # inject, skip the 2GB load
    vector = emb.embed_query("câu hỏi tiếng Việt")
    assert captured["texts"][0].startswith("query: ")  # e5 query prefix
    assert len(vector) == 1024
