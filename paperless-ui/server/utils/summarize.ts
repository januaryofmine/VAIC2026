import type { DocumentChunk } from "../types/retrieval";
import { groupChunks } from "./group-chunks";

/** Structured summary returned to the officer (deliverable #1). */
export interface StructuredSummary {
  context: string;
  main_content: string;
  decision_points: string[];
  impact: string;
}

/** LLM boundary — injected so the orchestration is unit-testable without a model. */
export interface Summarizer {
  mapSummary(text: string): Promise<string>;
  reduceSummary(partials: string[]): Promise<StructuredSummary>;
}

/** Run `fn` over items with at most `limit` in flight (avoids LLM rate-limit backoff). */
async function mapPool<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const i = next++;
      results[i] = await fn(items[i], i);
    }
  }
  const workers = Array.from({ length: Math.min(limit, items.length) }, worker);
  await Promise.all(workers);
  return results;
}

/**
 * Map-reduce summarization: summarize each group of chunks (map, concurrency-capped),
 * then combine the partial summaries into one structured summary (reduce).
 * Capping concurrency keeps us under the 60s budget without rate-limit backoff.
 */
export async function summarizeDocument(
  chunks: DocumentChunk[],
  summarizer: Summarizer,
  maxCharsPerGroup: number,
  maxConcurrency = 6,
): Promise<StructuredSummary> {
  if (chunks.length === 0) {
    throw new Error("cannot summarize an empty document");
  }
  const groups = groupChunks(chunks, maxCharsPerGroup);
  const partials = await mapPool(groups, maxConcurrency, (group) =>
    summarizer.mapSummary(group.map((c) => c.text).join("\n\n")),
  );
  return summarizer.reduceSummary(partials);
}
