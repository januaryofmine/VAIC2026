from chunk import chunk_blocks
from parse import Block

# Fake token counter = word count, so tests need no tokenizer/model.
wc = lambda t: len(t.split())  # noqa: E731


def sents(*markers: str, words: int = 4) -> str:
    """Build a paragraph of sentences, each 'MARKER x x ….' with `words` tokens."""
    return " ".join(m + " " + " ".join("x" for _ in range(words - 1)) + "." for m in markers)


def test_preserves_page_section_and_no_cross_section():
    blocks = [
        Block(sents("A", "B", "C"), page=1, section="Điều 1"),
        Block(sents("D", "E", "F"), page=2, section="Điều 2"),
    ]
    chunks = chunk_blocks(blocks, max_tokens=100, overlap_tokens=8, min_chars=1, count_tokens=wc)
    assert chunks[0].section == "Điều 1" and chunks[0].page == 1
    assert any(c.section == "Điều 2" and c.page == 2 for c in chunks)
    for c in chunks:  # no chunk mixes the two sections
        assert not (("A " in c.text or "B " in c.text) and ("D " in c.text or "E " in c.text))


def test_token_budget_never_exceeded():
    blocks = [Block(sents(*[f"S{i}" for i in range(20)]), page=1, section="Điều 1")]
    chunks = chunk_blocks(blocks, max_tokens=20, overlap_tokens=6, min_chars=1, count_tokens=wc)
    assert len(chunks) > 1
    assert all(wc(c.text) <= 20 for c in chunks)  # hard bound, incl. overlap seed


def test_consecutive_chunks_overlap():
    blocks = [Block(sents("P1", "P2", "P3"), page=1, section="Điều 1")]
    chunks = chunk_blocks(blocks, max_tokens=8, overlap_tokens=4, min_chars=1, count_tokens=wc)
    assert len(chunks) == 2
    assert "P1" in chunks[0].text and "P2" in chunks[0].text
    assert "P2" in chunks[1].text and "P3" in chunks[1].text  # P2 carried as overlap
    assert "P1" not in chunks[1].text


def test_positions_sequential():
    blocks = [Block(sents(*[f"S{i}" for i in range(10)]), page=1, section="Điều 1")]
    chunks = chunk_blocks(blocks, max_tokens=12, overlap_tokens=4, min_chars=1, count_tokens=wc)
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_oversized_sentence_is_sliced():
    big = "word " * 300  # one 300-word "sentence" (no delimiter)
    chunks = chunk_blocks([Block(big, page=1, section=None)], max_tokens=50, overlap_tokens=5, min_chars=1, count_tokens=wc)
    assert len(chunks) > 1
    assert all(wc(c.text) <= 60 for c in chunks)  # slack for proportional slicing


def test_min_chars_drops_noise():
    blocks = [
        Block(sents("A", "B"), page=1, section="Điều 1"),
        Block("x", page=1, section=None),  # tiny noise in its own section group
    ]
    chunks = chunk_blocks(blocks, max_tokens=100, overlap_tokens=8, min_chars=5, count_tokens=wc)
    assert all(c.text.strip() != "x" for c in chunks)


def test_empty_blocks_give_no_chunks():
    assert chunk_blocks([], count_tokens=wc) == []
