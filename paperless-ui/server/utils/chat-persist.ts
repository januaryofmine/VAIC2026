import { generateId } from "ai";

import type { ChatMessage } from "../types/retrieval";

/**
 * Build the assistant message to persist from the streamed text + its metadata
 * (sources/plan). Pure aside from the generated id, which can be injected for tests.
 */
export function buildAssistantMessage(
  text: string,
  metadata: { sources: unknown[]; plan: string[] },
  id: string = generateId(),
): ChatMessage {
  return {
    id,
    role: "assistant",
    parts: [{ type: "text", text }],
    metadata,
  };
}
