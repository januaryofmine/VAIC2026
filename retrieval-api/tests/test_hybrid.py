from app.services.retrieval import build_ts_query, rrf_fuse


def test_build_ts_query_or_prefixes_dropping_stopwords():
    assert (
        build_ts_query("Quan điểm của quyết định là gì?")
        == "quan:* | điểm:* | quyết:* | định:*"
    )


def test_build_ts_query_lowercases_and_dedupes():
    assert build_ts_query("Điều Điều quan trọng") == "điều:* | quan:* | trọng:*"


def test_build_ts_query_none_when_no_content():
    assert build_ts_query("của này là gì và") is None


def test_rrf_fuse_ranks_items_appearing_in_both_lists_higher():
    scores = rrf_fuse([["a", "b", "c"], ["b", "x", "a"]], k=60)
    # b is high in both lists; a is in both but lower; c only once
    assert scores["b"] > scores["a"] > scores["c"]
    assert scores["a"] > scores["x"]
