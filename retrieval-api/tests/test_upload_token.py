"""HMAC upload-token verify/sign. The known-vector test pins the exact bytes so the
Python verify and the Node signer (paperless-ui/server/utils/upload-token.ts) stay
interoperable — if either side changes the scheme, this breaks."""

from app.services.upload_token import make_upload_token, verify_upload_token

SECRET = "secret123"
# HMAC-SHA256(key="secret123", msg="user-1.1800000000") — MUST equal the Node output.
KNOWN = "35320dac356c83b594a830d7a2446eef9c4dcb9039a8bdd767d2c140ae6995ce"


def test_known_vector_matches_node():
    assert make_upload_token("user-1", SECRET, exp=1800000000) == f"user-1.1800000000.{KNOWN}"


def test_verify_valid_returns_user_id():
    tok = make_upload_token("u-abc", SECRET, exp=1800000000)
    assert verify_upload_token(tok, SECRET, now=1799999000) == "u-abc"


def test_verify_rejects_expired():
    tok = make_upload_token("u-abc", SECRET, exp=1800000000)
    assert verify_upload_token(tok, SECRET, now=1800000001) is None


def test_verify_rejects_tampered_signature():
    tok = make_upload_token("u-abc", SECRET, exp=1800000000)
    bad = tok[:-1] + ("0" if tok[-1] != "0" else "1")
    assert verify_upload_token(bad, SECRET, now=1799999000) is None


def test_verify_rejects_swapped_user_id():
    # attacker keeps a valid signature but swaps the user_id → must fail
    tok = make_upload_token("u-abc", SECRET, exp=1800000000)
    _, exp_s, sig = tok.split(".")
    assert verify_upload_token(f"attacker.{exp_s}.{sig}", SECRET, now=1799999000) is None


def test_verify_rejects_wrong_secret():
    tok = make_upload_token("u-abc", SECRET, exp=1800000000)
    assert verify_upload_token(tok, "othersecret", now=1799999000) is None


def test_verify_rejects_malformed():
    for bad in ("", "garbage", "a.b", "a.b.c.d"):
        assert verify_upload_token(bad, SECRET, now=1) is None
