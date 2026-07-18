import { describe, expect, it } from "vitest";

import { docFileUrl, viewerModeFor } from "./doc-viewer";

describe("viewerModeFor", () => {
  it("renders PDFs in the pdf viewer", () => {
    expect(viewerModeFor("pdf")).toBe("pdf");
  });
  it("normalizes case", () => {
    expect(viewerModeFor("PDF")).toBe("pdf");
  });
  it("treats docx as unsupported (falls back to download until 15b)", () => {
    expect(viewerModeFor("docx")).toBe("unsupported");
  });
  it("treats unknown/undefined as unsupported", () => {
    expect(viewerModeFor(undefined)).toBe("unsupported");
    expect(viewerModeFor("")).toBe("unsupported");
  });
});

describe("docFileUrl", () => {
  it("points at the document file proxy", () => {
    expect(docFileUrl("abc-123")).toBe("/api/documents/abc-123/file");
  });
});
