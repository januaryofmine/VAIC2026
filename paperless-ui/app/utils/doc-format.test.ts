import { describe, expect, it } from "vitest";

import { docTypeLabel, formatUploadedAt, isReady, statusMeta } from "./doc-format";

describe("statusMeta", () => {
  it("maps ready/failed/processing to label + kind", () => {
    expect(statusMeta("ready")).toEqual({ label: "Sẵn sàng", kind: "ok" });
    expect(statusMeta("failed")).toEqual({ label: "Lỗi xử lý", kind: "err" });
    expect(statusMeta("embedding")).toEqual({ label: "Đang xử lý", kind: "warn" });
    expect(statusMeta("pending").kind).toBe("warn");
  });
});

describe("isReady / docTypeLabel", () => {
  it("isReady only for 'ready'", () => {
    expect(isReady("ready")).toBe(true);
    expect(isReady("embedding")).toBe(false);
  });
  it("labels doc types", () => {
    expect(docTypeLabel("pdf")).toBe("PDF");
    expect(docTypeLabel("docx")).toBe("Word");
  });
});

describe("formatUploadedAt", () => {
  const now = new Date("2026-07-18T12:00:00");
  it("says Hôm nay for today", () => {
    expect(formatUploadedAt("2026-07-18T09:24:00+07", now)).toBe("Hôm nay, 09:24");
  });
  it("says Hôm qua for yesterday", () => {
    expect(formatUploadedAt("2026-07-17T16:10:00+07", now)).toBe("Hôm qua, 16:10");
  });
  it("uses DD/MM/YYYY for older dates", () => {
    expect(formatUploadedAt("2026-07-15T11:02:00+07", now)).toBe("15/07/2026, 11:02");
  });
});
