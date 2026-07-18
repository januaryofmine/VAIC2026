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
  // Authorize before any retrieval or LLM call: signed in AND owns this document.
  await requireDocumentAccess(event, document_id);

  const config = useRuntimeConfig();

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
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
          retrieveChunks(sq.query, document_id, [], ai.askTopK),
        ),
      );
      const chunks = mergeAndDedupe(results, ai.askMaxChunks);
      const system = assembleSystemPrompt(formatContext(chunks));

      const sources = chunks.map((c) => ({
        position: c.position,
        page: c.page,
        section: c.section,
        text: c.text,
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

      // Force the generation to finish server-side so onFinish (which persists the turn)
      // always runs — even if the client disconnects mid-stream, which would otherwise
      // stall generation and lose the whole turn. On serverless (Vercel) waitUntil keeps
      // the function alive until the save completes; it is undefined on the local
      // node-server preset, hence the optional call.
      const finished = result.consumeStream();
      event.context.waitUntil?.(finished);

      writer.merge(
        result.toUIMessageStream({
          messageMetadata: ({ part }) => {
            if (part.type === "start") return { sources, plan };
          },
        }),
      );
    },
  });

  return createUIMessageStreamResponse({ stream });
});
