from parse import detect_section


def test_detects_dieu():
    assert detect_section("Điều 5. Quyền sử dụng đất", None) == "Điều 5"


def test_keeps_current_when_no_header():
    assert detect_section("nội dung khoản a này", "Điều 5") == "Điều 5"


def test_normalises_whitespace():
    assert detect_section("Điều   12 phạm vi", None) == "Điều 12"


def test_none_stays_none_without_header():
    assert detect_section("phần mở đầu không đánh số", None) is None


def test_new_dieu_overrides_current():
    assert detect_section("Điều 6. Nguyên tắc", "Điều 5") == "Điều 6"
