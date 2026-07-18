import { describe, expect, it } from "vitest";
import { signUploadToken } from "./upload-token";

// Same known vector as retrieval-api/tests/test_upload_token.py — proves Node signs
// exactly what Python verifies. HMAC-SHA256("secret123", "user-1.1800000000").
const KNOWN = "35320dac356c83b594a830d7a2446eef9c4dcb9039a8bdd767d2c140ae6995ce";

describe("signUploadToken", () => {
  it("matches the shared known vector (interop with Python verify)", () => {
    const tok = signUploadToken("user-1", "secret123", {
      ttlSec: 300,
      nowMs: (1800000000 - 300) * 1000,
    });
    expect(tok).toBe(`user-1.1800000000.${KNOWN}`);
  });

  it("binds the user id and a future expiry", () => {
    const tok = signUploadToken("u-x", "s", { nowMs: 1_000_000, ttlSec: 300 });
    const [uid, exp, sig] = tok.split(".");
    expect(uid).toBe("u-x");
    expect(Number(exp)).toBe(Math.floor(1_000_000 / 1000) + 300);
    expect(sig).toMatch(/^[0-9a-f]{64}$/);
  });
});
