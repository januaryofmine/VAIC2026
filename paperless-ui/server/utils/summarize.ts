import type { DocumentChunk } from "../types/retrieval";
import { mapReduceDocument } from "./map-reduce";

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

/**
 * Map-reduce summarization (delegates to the shared engine): summarize each group
 * of chunks (map, concurrency-capped), then combine into one structured summary.
 */
export async function summarizeDocument(
  chunks: DocumentChunk[],
  summarizer: Summarizer,
  maxCharsPerGroup: number,
  maxConcurrency = 6,
): Promise<StructuredSummary> {
  return mapReduceDocument(
    chunks,
    {
      mapText: (text) => summarizer.mapSummary(text),
      reduce: (partials) => summarizer.reduceSummary(partials),
    },
    maxCharsPerGroup,
    maxConcurrency,
  );
}
