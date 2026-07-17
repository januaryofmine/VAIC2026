import type { DocumentChunk } from "../types/retrieval";
import { groupChunks } from "./group-chunks";

/** Run `fn` over items with at most `limit` in flight (avoids LLM rate-limit backoff). */
export async function mapPool<T, R>(
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
 * A map-reduce over a document's chunks. `mapText` condenses one group of chunk
 * text; `reduce` combines the ordered partials into the final result T.
 * Shared by summarize / terms / questions (the prep-pack endpoints).
 */
export interface MapReduce<T> {
  mapText(text: string): Promise<string>;
  reduce(partials: string[]): Promise<T>;
}

export async function mapReduceDocument<T>(
  chunks: DocumentChunk[],
  ops: MapReduce<T>,
  maxCharsPerGroup: number,
  maxConcurrency = 6,
): Promise<T> {
  if (chunks.length === 0) {
    throw new Error("cannot map-reduce an empty document");
  }
  const groups = groupChunks(chunks, maxCharsPerGroup);
  const partials = await mapPool(groups, maxConcurrency, (group) =>
    ops.mapText(group.map((c) => c.text).join("\n\n")),
  );
  return ops.reduce(partials);
}
