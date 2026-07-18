import { describe, expect, it } from "vitest";
import { apiKeyHeaders, buildIngestForm } from "./retrieval-http";

describe("apiKeyHeaders", () => {
  it("adds X-API-Key when a key is present", () => {
    expect(apiKeyHeaders("secret")).toEqual({ "X-API-Key": "secret" });
  });

  it("omits the header for local dev (empty / undefined key)", () => {
    expect(apiKeyHeaders("")).toEqual({});
    expect(apiKeyHeaders(undefined)).toEqual({});
  });
});

describe("buildIngestForm", () => {
  it("carries the file under its original name plus the owner id", () => {
    const fd = buildIngestForm(new Uint8Array([1, 2, 3]), "Luật QĐ.pdf", "u-123");
    const file = fd.get("file");
    expect(file).toBeInstanceOf(Blob);
    expect((file as File).name).toBe("Luật QĐ.pdf");
    expect(fd.get("user_id")).toBe("u-123");
  });

  it("omits user_id when there is no owner", () => {
    const fd = buildIngestForm(new Uint8Array([1]), "x.pdf");
    expect(fd.get("user_id")).toBeNull();
  });
});
