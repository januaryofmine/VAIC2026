import { createAnthropic } from "@ai-sdk/anthropic";
import { instrumentFetch } from "./llm-trace";

// The AI SDK reads ANTHROPIC_API_KEY from the environment when no apiKey is passed.
// `instrumentFetch` gửi trace mỗi lời gọi LLM (latency/token/prompt) lên Langfuse —
// đây là CHOKEPOINT nên mọi điểm gọi (summarize / terms / questions / chat) đều được
// bao mà không phải sửa từng nơi. Là no-op khi chưa đặt LANGFUSE_* (xem llm-trace.ts).
export function getModel(model: string) {
  return createAnthropic({ fetch: instrumentFetch(globalThis.fetch) })(model);
}
