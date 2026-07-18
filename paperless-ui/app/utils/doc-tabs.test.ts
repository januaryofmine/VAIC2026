import { describe, expect, it } from "vitest";

import { buildDocTabs } from "./doc-tabs";

describe("buildDocTabs", () => {
  it("returns the four tabs in a fixed order", () => {
    const tabs = buildDocTabs({ terms: null, questions: null });
    expect(tabs.map((t) => t.value)).toEqual(["summary", "terms", "questions", "chat"]);
  });

  it("appends counts to terms and questions when known", () => {
    const tabs = buildDocTabs({ terms: 12, questions: 6 });
    const byValue = Object.fromEntries(tabs.map((t) => [t.value, t.label]));
    expect(byValue.terms).toBe("Thuật ngữ 12");
    expect(byValue.questions).toBe("Câu hỏi 6");
  });

  it("omits the count while still loading (null)", () => {
    const tabs = buildDocTabs({ terms: null, questions: null });
    const byValue = Object.fromEntries(tabs.map((t) => [t.value, t.label]));
    expect(byValue.terms).toBe("Thuật ngữ");
    expect(byValue.questions).toBe("Câu hỏi");
  });

  it("keeps summary and chat labels count-free", () => {
    const tabs = buildDocTabs({ terms: 3, questions: 4 });
    const byValue = Object.fromEntries(tabs.map((t) => [t.value, t.label]));
    expect(byValue.summary).toBe("Tóm tắt");
    expect(byValue.chat).toBe("Hỏi đáp");
  });

  it("gives every tab an icon", () => {
    const tabs = buildDocTabs({ terms: 1, questions: 1 });
    expect(tabs.every((t) => t.icon.length > 0)).toBe(true);
  });
});
