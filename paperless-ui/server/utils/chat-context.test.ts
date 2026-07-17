import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";

import type { RetrieveChunk } from "../types/retrieval";
import {
  assembleSystemPrompt,
  extractConversationHistory,
  extractQuestion,
  formatContext,
} from "./chat-context";

const msg = (role: "user" | "assistant", text: string): UIMessage =>
  ({ id: `${role}-${text}`, role, parts: [{ type: "text", text }] }) as unknown as UIMessage;

const chunk = (over: Partial<RetrieveChunk>): RetrieveChunk => ({
  id: "1",
  position: 0,
  page: null,
  section: null,
  text: "nội dung",
  score: 0.9,
  ...over,
});

describe("extractQuestion", () => {
  it("returns the latest user message text", () => {
    const out = extractQuestion([msg("user", "câu 1"), msg("assistant", "trả lời"), msg("user", "câu 2")]);
    expect(out?.question).toBe("câu 2");
  });

  it("returns null when there is no user message", () => {
    expect(extractQuestion([msg("assistant", "hi")])).toBeNull();
  });
});

describe("extractConversationHistory", () => {
  it("excludes the current question, keeps text turns, caps at 6", () => {
    const msgs = [
      msg("user", "u1"),
      msg("assistant", "a1"),
      msg("user", "u2"),
      msg("assistant", "a2"),
      msg("user", "u3"),
      msg("assistant", "a3"),
      msg("user", "u4"),
      msg("user", "current"),
    ];
    const current = msgs[msgs.length - 1];
    const history = extractConversationHistory(msgs, current);
    expect(history.length).toBe(6);
    expect(history.every((h) => h.content !== "current")).toBe(true);
    expect(history[0]).toEqual({ role: "assistant", content: "a1" });
  });
});

describe("formatContext", () => {
  it("adds a page+section citation label (PDF)", () => {
    const out = formatContext([chunk({ page: 3, section: "Điều 1", text: "abc" })]);
    expect(out).toContain("[1] (trang 3, Điều 1)");
    expect(out).toContain("abc");
  });

  it("uses only section when page is null (DOCX)", () => {
    const out = formatContext([chunk({ page: null, section: "Điều 5" })]);
    expect(out).toContain("(Điều 5)");
    expect(out).not.toContain("trang");
  });

  it("numbers multiple chunks", () => {
    const out = formatContext([chunk({ page: 1 }), chunk({ page: 2 })]);
    expect(out).toContain("[1] (trang 1)");
    expect(out).toContain("[2] (trang 2)");
  });
});

describe("assembleSystemPrompt", () => {
  it("wraps context and instructs page/Điều citation", () => {
    const out = assembleSystemPrompt("CTX");
    expect(out).toContain("<context>\nCTX\n</context>");
    expect(out).toContain("trang/Điều");
  });
});
