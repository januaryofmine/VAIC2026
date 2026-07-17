from chunk import chunk_blocks
from parse import Block


def test_preserves_page_and_section():
    blocks = [
        Block("a" * 300, page=1, section="Điều 1"),
        Block("b" * 300, page=2, section="Điều 2"),
    ]
    chunks = chunk_blocks(blocks, max_chars=1000, min_chars=50)
    assert chunks[0].page == 1 and chunks[0].section == "Điều 1"
    assert any(c.page == 2 and c.section == "Điều 2" for c in chunks)


def test_positions_are_sequential():
    blocks = [Block("x" * 300, 1, None), Block("y" * 300, 1, None), Block("z" * 300, 2, None)]
    chunks = chunk_blocks(blocks, max_chars=250, min_chars=10)
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_oversized_block_is_split():
    big = ("paragraph.\n\n" * 400).strip()  # many small paragraphs
    chunks = chunk_blocks([Block(big, page=1, section=None)], max_chars=500, min_chars=50)
    assert len(chunks) > 1
    assert all(len(c.text) <= 500 for c in chunks)


def test_small_same_scope_merged():
    blocks = [Block("short one", 1, "Điều 1"), Block("short two", 1, "Điều 1")]
    chunks = chunk_blocks(blocks, max_chars=1000, min_chars=100)
    assert len(chunks) == 1
    assert "short one" in chunks[0].text and "short two" in chunks[0].text


def test_small_different_section_not_merged():
    blocks = [Block("short one", 1, "Điều 1"), Block("short two", 1, "Điều 2")]
    chunks = chunk_blocks(blocks, max_chars=1000, min_chars=100)
    assert len(chunks) == 2


def test_empty_blocks_give_no_chunks():
    assert chunk_blocks([]) == []
