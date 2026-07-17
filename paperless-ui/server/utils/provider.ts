import { createAnthropic } from "@ai-sdk/anthropic";

// The AI SDK reads ANTHROPIC_API_KEY from the environment when no apiKey is passed.
export function getModel(model: string) {
  return createAnthropic()(model);
}
