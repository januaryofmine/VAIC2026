import type { DocumentChunk } from "../types/retrieval";

/**
 * Pack chunks (in order) into groups whose combined text stays under maxChars.
 * A single oversized chunk becomes its own group. Used for map-reduce so the
 * "map" step over a long document fits comfortably in one LLM call.
 */
export function groupChunks(
  chunks: DocumentChunk[],
  maxChars: number,
): DocumentChunk[][] {
  const groups: DocumentChunk[][] = [];
  let current: DocumentChunk[] = [];
  let size = 0;

  for (const chunk of chunks) {
    if (current.length > 0 && size + chunk.text.length > maxChars) {
      groups.push(current);
      current = [];
      size = 0;
    }
    current.push(chunk);
    size += chunk.text.length;
  }
  if (current.length > 0) groups.push(current);

  return groups;
}
