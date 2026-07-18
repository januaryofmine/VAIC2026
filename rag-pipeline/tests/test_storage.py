from pathlib import Path

from storage import BlobStorage, sha256_file


def _write(p: Path, data: bytes) -> Path:
    p.write_bytes(data)
    return p


def test_sha256_matches_known_value(tmp_path):
    f = _write(tmp_path / "a.pdf", b"hello")
    # sha256("hello")
    assert sha256_file(f) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_path_for_is_deterministic_and_scoped(tmp_path):
    s = BlobStorage(tmp_path)
    p = s.path_for("abc123", "PDF")
    assert p == tmp_path / "documents" / "abc123.pdf"  # ext lowercased, under documents/


def test_save_copies_bytes_and_returns_absolute_path(tmp_path):
    src = _write(tmp_path / "src.pdf", b"%PDF-1.4 data")
    s = BlobStorage(tmp_path / "store")
    out = s.save("hashaaa", "pdf", src)
    assert Path(out).is_absolute()
    assert Path(out).read_bytes() == b"%PDF-1.4 data"
    assert s.exists("hashaaa", "pdf")


def test_save_is_idempotent_dedup(tmp_path):
    src = _write(tmp_path / "src.pdf", b"same content")
    s = BlobStorage(tmp_path / "store")
    first = s.save("h", "pdf", src)
    # a second file with the SAME hash key must not overwrite / error → same path
    other = _write(tmp_path / "other.pdf", b"IGNORED - dedup keeps the first")
    second = s.save("h", "pdf", other)
    assert first == second
    assert Path(first).read_bytes() == b"same content"  # first write preserved
