import { createHmac } from "node:crypto";

/**
 * Sign a short-lived HMAC upload token so the browser can POST a file straight to
 * retrieval-api `/api/ingest` (bypassing Vercel's 4.5MB function-body limit) without
 * ever seeing the API key. The token binds the owner user id + an expiry;
 * retrieval-api verifies it (see retrieval-api/app/services/upload_token.py).
 *
 * Format: `<userId>.<expUnixSeconds>.<hmacSha256Hex>` — identical bytes to the
 * Python verifier (utf-8 message, hex digest); the shared known-vector test guards it.
 */
export function signUploadToken(
  userId: string,
  secret: string,
  opts: { ttlSec?: number; nowMs?: number } = {},
): string {
  const ttl = opts.ttlSec ?? 300;
  const nowMs = opts.nowMs ?? Date.now();
  const exp = Math.floor(nowMs / 1000) + ttl;
  const sig = createHmac("sha256", secret).update(`${userId}.${exp}`).digest("hex");
  return `${userId}.${exp}.${sig}`;
}
