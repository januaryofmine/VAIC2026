import numpy as np

import embed
from config import config as cfg
from tests.fakes import FakeEmbedder


def test_fake_embedder_dim_and_count():
    e = FakeEmbedder(dim=1024)
    vecs = e.embed_documents(["a", "bb", "ccc"])
    assert len(vecs) == 3
    assert all(len(v) == 1024 for v in vecs)


def test_prefixes_configured_for_e5():
    assert cfg.embedding_prefix_document == "passage: "
    assert cfg.embedding_prefix_query == "query: "


def test_e5_applies_passage_prefix_without_loading_model():
    captured = {}

    class FakeModel:
        def encode(self, texts, **kwargs):
            captured["texts"] = texts
            return np.zeros((len(texts), 4))

    e = embed.E5Embedder()
    e._model = FakeModel()  # inject, skip the 2GB load
    e.embed_documents(["hello world"])
    assert captured["texts"][0].startswith("passage: ")


def test_e5_applies_query_prefix_without_loading_model():
    captured = {}

    class FakeModel:
        def encode(self, texts, **kwargs):
            captured["texts"] = texts
            return np.zeros((len(texts), 4))

    e = embed.E5Embedder()
    e._model = FakeModel()
    e.embed_query("tìm gì đó")
    assert captured["texts"][0].startswith("query: ")
