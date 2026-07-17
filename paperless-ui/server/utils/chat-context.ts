import type { UIMessage } from "ai";

import type { RetrieveChunk } from "../types/retrieval";

export interface HistoryEntry {
  role: "user" | "assistant";
  content: string;
}

function textOf(message: UIMessage): string {
  return (
    message.parts
      ?.filter((p) => p.type === "text")
      .map((p) => (p as { text: string }).text)
      .join("") ?? ""
  );
}

/** The latest user message + its plain text (the question to answer). */
export function extractQuestion(
  messages: UIMessage[],
): { question: string; lastUserMessage: UIMessage } | null {
  const lastUserMessage = [...messages].reverse().find((m) => m.role === "user");
  if (!lastUserMessage) return null;
  return { question: textOf(lastUserMessage), lastUserMessage };
}

/** Prior turns (text-only, last 6, excluding the current question) for reformulation. */
export function extractConversationHistory(
  messages: UIMessage[],
  lastUserMessage: UIMessage,
): HistoryEntry[] {
  return messages
    .filter((m) => m !== lastUserMessage)
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({ role: m.role as "user" | "assistant", content: textOf(m) }))
    .filter((m) => m.content.length > 0)
    .slice(-6);
}

/** Format retrieved chunks with a page/Điều citation label so the model can cite them. */
export function formatContext(chunks: RetrieveChunk[]): string {
  return chunks
    .map((c, i) => {
      const cite = [
        c.page != null ? `trang ${c.page}` : null,
        c.section,
      ]
        .filter(Boolean)
        .join(", ");
      const label = cite ? `[${i + 1}] (${cite})` : `[${i + 1}]`;
      return `${label}\n${c.text}`;
    })
    .join("\n\n---\n\n");
}

export const CHAT_SYSTEM_PROMPT =
  "Bạn là trợ lý giúp cán bộ hiểu tài liệu chuẩn bị họp. Trả lời bằng tiếng Việt, ngắn gọn, " +
  "chính xác, CHỈ dựa trên phần <context> được cung cấp. Nếu context không đủ để trả lời, hãy " +
  "nói rõ là không tìm thấy trong tài liệu. LUÔN trích dẫn nguồn theo trang/Điều trong ngoặc " +
  "ngay sau ý liên quan, ví dụ: (trang 3, Điều 1).";

export function assembleSystemPrompt(context: string): string {
  return `${CHAT_SYSTEM_PROMPT}\n\n<context>\n${context}\n</context>`;
}
