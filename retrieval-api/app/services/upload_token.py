"""Short-lived HMAC upload tokens for direct browser→retrieval-api uploads.

Vercel serverless functions cap the request body at 4.5MB, so large documents can't
be proxied through the Nuxt BFF. Instead the browser POSTs the file straight to
`/api/ingest`. The BFF (which holds the user session + the shared secret) signs a
token binding the owner user_id + an expiry; retrieval-api verifies the HMAC. The
file never transits the UI host and the API_KEY is never exposed to the browser.

Node's `crypto.createHmac("sha256")` and this module produce identical tokens
(utf-8 message, hex digest) — see paperless-ui/server/utils/upload-token.ts and the
shared known-vector test.

Token format:  <user_id>.<exp_unix_seconds>.<hmac_sha256_hex>
"""

from __future__ import annotations

import hashlib
import hmac
import time


def make_upload_token(user_id: str, secret: str, exp: int) -> str:
    sig = hmac.new(secret.encode(), f"{user_id}.{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{user_id}.{exp}.{sig}"


def verify_upload_token(token: str, secret: str, now: int | None = None) -> str | None:
    """Return the signed user_id if `token` is a valid, unexpired HMAC for `secret`;
    otherwise None. Never raises."""
    if not token or token.count(".") != 2:
        return None
    user_id, exp_s, sig = token.split(".")
    try:
        exp = int(exp_s)
    except ValueError:
        return None
    expected = hmac.new(
        secret.encode(), f"{user_id}.{exp}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    if exp < (now if now is not None else int(time.time())):
        return None
    return user_id
