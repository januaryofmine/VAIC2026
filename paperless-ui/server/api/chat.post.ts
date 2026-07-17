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

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const extracted = extractQuestion(messages);
      if (!extracted) {
        throw createError({ statusCode: 400, statusMessage: "no user message" });
      }
      const { question, lastUserMessage } = extracted;
      const history = extractConversationHistory(messages, lastUserMessage);

      // Q&A path: vector search scoped to this document, then answer with citations.
      const retrieved = await retrieveChunks(question, document_id, history);
      const system = assembleSystemPrompt(formatContext(retrieved.chunks));

      const sources = retrieved.chunks.map((c) => ({
        position: c.position,
        page: c.page,
        section: c.section,
      }));

      const recent =
        messages.length > MAX_MESSAGES ? messages.slice(-MAX_MESSAGES) : messages;

      const result = streamText({
        model: getModel(config.ai.chatModel),
        temperature: config.ai.temperature,
        system,
        messages: await convertToModelMessages(recent),
      });

      writer.merge(
        result.toUIMessageStream({
          messageMetadata: ({ part }) => {
            if (part.type === "start") return { sources };
          },
        }),
      );
    },
  });

  return createUIMessageStreamResponse({ stream });
});
