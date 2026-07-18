import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

/**
 * LLM provider selection (env-driven, defaults unchanged).
 *
 * - `anthropic` (default): Claude via ANTHROPIC_API_KEY — the production path.
 * - `openai-compatible`: any OpenAI-style gateway (e.g. 9router on :20128/v1),
 *   which is how the project runs when no Anthropic key is available.
 *
 * Reasoning models (deepseek-v4-flash, …) spend their whole token budget on hidden
 * "thinking" and return EMPTY content — the summary comes back blank and the run
 * blows the <60s budget. Setting `reasoning_effort: "none"` fixes it, so when
 * `ai.disableReasoning` is on we inject it into every request body here; no call
 * site (summarizer / terms / questions / chat) needs to know.
 */
export function getModel(model: string) {
  const { ai } = useRuntimeConfig();

  if (ai.provider !== "openai-compatible") {
    // The AI SDK reads ANTHROPIC_API_KEY from the environment when no apiKey is passed.
    return createAnthropic()(model);
  }

  const gateway = createOpenAICompatible({
    name: "gateway",
    baseURL: ai.baseUrl,
    apiKey: ai.apiKey || "unused", // local gateways typically need no key
    // Make the SDK emit the JSON schema; the fetch below rewrites it into the
    // json_object form gateways actually accept (see makeGatewayFetch).
    supportsStructuredOutputs: true,
    fetch: makeGatewayFetch(ai.disableReasoning),
  });
  return gateway(model);
}

/**
 * Wrapping fetch that normalises gateway quirks:
 * - `reasoning_effort: "none"` so reasoning models emit real content (see above);
 * - `stream: false` when the SDK didn't ask to stream — 9router otherwise replies
 *   with SSE to a non-streaming call and the SDK fails on "Invalid JSON response".
 *   (streamText sets stream:true itself, so streaming still works.)
 * - `response_format: json_schema` → `json_object` + the schema appended to the
 *   prompt. Many gateway models reject json_schema (400) but accept json_object;
 *   the SDK still validates the parsed object against the zod schema afterwards.
 *   This is what keeps summarize / terms / questions working off-Anthropic.
 */
function makeGatewayFetch(disableReasoning: boolean): typeof globalThis.fetch {
  return async (input, init) => {
    if (init?.body && typeof init.body === "string") {
      try {
        const body = JSON.parse(init.body);
        if (disableReasoning) body.reasoning_effort = "none";
        if (body.stream === undefined) body.stream = false;

        if (body.response_format?.type === "json_schema") {
          const schema = body.response_format.json_schema?.schema;
          body.response_format = { type: "json_object" };
          const last = body.messages?.[body.messages.length - 1];
          if (schema && last && typeof last.content === "string") {
            last.content +=
              "\n\nCHỈ trả về một JSON hợp lệ đúng schema sau, không kèm chữ nào khác:\n" +
              JSON.stringify(schema);
          }
        }
        // OpenAI-style json_object mode REJECTS (400) any request whose messages
        // don't mention "json" — our prompts are Vietnamese, so add the hint.
        if (body.response_format?.type === "json_object" && Array.isArray(body.messages)) {
          const mentionsJson = body.messages.some(
            (m: { content?: unknown }) =>
              typeof m.content === "string" && /json/i.test(m.content),
          );
          const last = body.messages[body.messages.length - 1];
          if (!mentionsJson && last && typeof last.content === "string") {
            last.content += "\n\nCHỈ trả về một JSON hợp lệ, không kèm chữ nào khác.";
          }
        }
        init = { ...init, body: JSON.stringify(body) };
      } catch {
        // non-JSON body — send it through untouched
      }
    }
    return globalThis.fetch(input, init);
  };
}
