import { describe, expect, it } from "vitest";

import { stripLeadingEnumeration } from "./questions-format";

describe("stripLeadingEnumeration", () => {
  it("strips a '1. ' prefix", () => {
    expect(stripLeadingEnumeration("1. Mục tiêu chính là gì?")).toBe("Mục tiêu chính là gì?");
  });
  it("strips a '2) ' prefix", () => {
    expect(stripLeadingEnumeration("2) Vì sao lại chọn phương án này?")).toBe(
      "Vì sao lại chọn phương án này?",
    );
  });
  it("strips multi-digit prefixes", () => {
    expect(stripLeadingEnumeration("12. Câu hỏi thứ mười hai?")).toBe("Câu hỏi thứ mười hai?");
  });
  it("leaves text without a leading number untouched", () => {
    expect(stripLeadingEnumeration("Vì sao ngân sách bị cắt giảm?")).toBe(
      "Vì sao ngân sách bị cắt giảm?",
    );
  });
  it("does not touch a number that appears mid-sentence", () => {
    expect(stripLeadingEnumeration("Điều 4 quy định gì về việc này?")).toBe(
      "Điều 4 quy định gì về việc này?",
    );
  });
});
