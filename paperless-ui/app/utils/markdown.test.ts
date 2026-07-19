import { describe, expect, it } from "vitest";

import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("renders **bold** as <strong>", () => {
    expect(renderMarkdown("bị **xem xét thu hồi vốn** (Điều 4)")).toBe(
      "bị <strong>xem xét thu hồi vốn</strong> (Điều 4)",
    );
  });
  it("renders *italic* as <em>", () => {
    expect(renderMarkdown("có *nghiêng* ở đây")).toBe("có <em>nghiêng</em> ở đây");
  });
  it("renders `code` as <code>", () => {
    expect(renderMarkdown("dùng `npm run dev`")).toBe("dùng <code>npm run dev</code>");
  });
  it("escapes HTML to prevent XSS", () => {
    expect(renderMarkdown("<script>alert(1)</script>")).toBe(
      "&lt;script&gt;alert(1)&lt;/script&gt;",
    );
  });
  it("converts newlines to <br>", () => {
    expect(renderMarkdown("dòng 1\ndòng 2")).toBe("dòng 1<br>dòng 2");
  });
});
