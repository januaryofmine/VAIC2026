import { describe, expect, it } from "vitest";

import { buildAssistantMessage } from "./chat-persist";

describe("buildAssistantMessage", () => {
  it("wraps text as a UIMessage part and keeps sources/plan metadata", () => {
    const msg = buildAssistantMessage(
      "Trả lời có trích dẫn.",
      { sources: [{ page: 3, section: "Điều 1" }], plan: ["q1", "q2"] },
      "fixed-id",
    );
    expect(msg).toEqual({
      id: "fixed-id",
      role: "assistant",
      parts: [{ type: "text", text: "Trả lời có trích dẫn." }],
      metadata: { sources: [{ page: 3, section: "Điều 1" }], plan: ["q1", "q2"] },
    });
  });

  it("generates an id when none is given", () => {
    const a = buildAssistantMessage("a", { sources: [], plan: [] });
    const b = buildAssistantMessage("b", { sources: [], plan: [] });
    expect(a.id).toBeTruthy();
    expect(a.id).not.toBe(b.id);
  });
});
