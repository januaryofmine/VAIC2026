import { describe, expect, it } from "vitest";

import { detectDocType, parseDocumentId } from "./ingest-runner";

describe("detectDocType", () => {
  it("accepts pdf and docx (case-insensitive)", () => {
    expect(detectDocType("report.pdf")).toBe("pdf");
    expect(detectDocType("LAW.DOCX")).toBe("docx");
    expect(detectDocType("a.b.c.pdf")).toBe("pdf");
  });

  it("rejects unsupported / extensionless names", () => {
    expect(detectDocType("notes.txt")).toBeNull();
    expect(detectDocType("image.png")).toBeNull();
    expect(detectDocType("noext")).toBeNull();
  });
});

describe("parseDocumentId", () => {
  it("extracts the uuid ingest.py prints", () => {
    const stdout =
      "document_id=552fdac4-810b-4e3a-b9f3-08e1bbb6ad3e  chunks=278  with_page=278  with_section=272\n";
    expect(parseDocumentId(stdout)).toBe("552fdac4-810b-4e3a-b9f3-08e1bbb6ad3e");
  });

  it("returns null when no document_id is present", () => {
    expect(parseDocumentId("Traceback... error\n")).toBeNull();
    expect(parseDocumentId("")).toBeNull();
  });
});
