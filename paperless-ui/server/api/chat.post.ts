import type { UIMessage } from "ai";
import {
  convertToModelMessages,
  createUIMessageStream,
  createUIMessageStreamResponse,
  streamText,
} from "ai";

const MAX_MESSAGES = 20;

export default defineEventHandler(async (event) => {
  const { messages, document_id } = await readBody<{
    messages: UIMessage[];
    document_id?: string;
  }>(event);

  if (!document_id) {
    throw createError({ statusCode: 400, statusMessage: "document_id is required" });
  }
  if (!messages?.length) {
    throw createError({ statusCode: 400, statusMessage: "messages are required" });
  }

  const config = useRuntimeConfig();

  // AI monitoring: một id cho cả câu hỏi. Mọi lời gọi LLM bên trong (lập kế hoạch,
  // sinh câu trả lời) tự nhặt id này qua AsyncLocalStorage, còn retrieval-api nhận
  // qua header X-Trace-Id → Langfuse hiện MỘT trace UI→RAG→LLM thay vì các mảnh rời.
  const traceId = newTraceId();

  const stream = createUIMessageStream({
    execute: async ({ writer }) => runWithTrace(traceId, async () => {
      const extracted = extractQuestion(messages);
      if (!extracted) {
        throw createError({ statusCode: 400, statusMessage: "no user message" });
      }
      const { question, lastUserMessage } = extracted;
      const history = extractConversationHistory(messages, lastUserMessage);
      const { ai } = config;

      // Plan-and-fan-out Q&A: plan a few focused sub-queries, run each through the
      // hybrid retriever in parallel, then RRF-merge before answering with citations.
      // Sub-queries are self-contained (planning already used history), so each
      // retrieve gets empty history to avoid double reformulation.
      const strategy = await planStrategy(question, history, ai.planModel, ai.temperature);
      const results = await Promise.all(
        strategy.subqueries.map((sq) =>
          retrieveChunks(sq.query, document_id, [], ai.askTopK, traceId),
        ),
      );
      const chunks = mergeAndDedupe(results, ai.askMaxChunks);
      const system = assembleSystemPrompt(formatContext(chunks));

      const sources = chunks.map((c) => ({
        position: c.position,
        page: c.page,
        section: c.section,
      }));

      // Surface the search plan (the sub-queries the retriever fanned out on) so the
      // UI can show "đang tìm: …" and so the strategy is observable in the stream.
      const plan = strategy.subqueries.map((s) => s.query);

      const recent =
        messages.length > MAX_MESSAGES ? messages.slice(-MAX_MESSAGES) : messages;

      const result = streamText({
        model: getModel(config.ai.chatModel),
        temperature: config.ai.temperature,
        system,
        messages: await convertToModelMessages(recent),
        // Persist the whole turn (question + answer with citations) only once streaming
        // completes, so a failed/interrupted stream never leaves an orphan user message.
        // Best-effort — a save failure never breaks the reply.
        onFinish: async ({ text }) => {
          try {
            await appendChatMessage(document_id, {
              id: lastUserMessage.id,
              role: "user",
              parts: lastUserMessage.parts,
            });
            await appendChatMessage(document_id, buildAssistantMessage(text, { sources, plan }));
          } catch (e) {
            console.error("[chat] save messages failed:", e);
          }
        },
      });

      writer.merge(
        result.toUIMessageStream({
          messageMetadata: ({ part }) => {
            if (part.type === "start") return { sources, plan };
          },
        }),
      );
    }),
  });

  return createUIMessageStreamResponse({ stream });
});
