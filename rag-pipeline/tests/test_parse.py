from parse import Block, _blocks_from_pages, pages_from_pdftotext


def test_section_header_mid_block_is_detected():
    # "Điều 1" is NOT at the paragraph start — it follows another line in the
    # same blank-line-delimited block (the exact case that was returning 0).
    page = "Preamble line\nĐiều 1. Nội dung\nchi tiết điều 1\n\nĐiều 2. Khác\nnội dung 2"
    blocks = _blocks_from_pages([page])
    sections = {b.section for b in blocks}
    assert "Điều 1" in sections
    assert "Điều 2" in sections
    # text before the first article carries no section
    assert any(b.section is None and "Preamble" in b.text for b in blocks)


def test_article_text_tagged_with_its_section():
    page = "header noise\nĐiều 5. Quy định\nnội dung của điều năm"
    blocks = _blocks_from_pages([page])
    art = next(b for b in blocks if "nội dung của điều năm" in b.text)
    assert art.section == "Điều 5"


def test_page_numbers_assigned_across_pages():
    blocks = _blocks_from_pages(["text on page one", "text on page two"])
    assert blocks[0].page == 1
    assert blocks[1].page == 2


def test_pages_from_pdftotext_splits_on_formfeed():
    assert pages_from_pdftotext("page1\x0cpage2\x0cpage3") == ["page1", "page2", "page3"]
