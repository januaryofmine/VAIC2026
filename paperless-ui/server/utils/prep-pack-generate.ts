import { createError } from "h3";

import type { FullDocument, PrepPackKind } from "../types/retrieval";
import type { StructuredSummary } from "./summarize";

/**
 * Per-kind LLM compute (map-reduce). Single source of truth shared by the on-open
 * endpoints (summarize/terms/questions) AND the backend-driven ingest trigger, so the
 * generation logic lives in exactly one place.
 */
export const prepComputers = {
  summary: (doc: FullDocument): Promise<StructuredSummary> => {
    const { ai } = useRuntimeConfig();
    return summarizeDocument(
      doc.chunks,
      createAnthropicSummarizer(),
      ai.mapGroupChars,
      ai.mapConcurrency,
    );
  },
  terms: async (doc: FullDocument) => {
    const { ai } = useRuntimeConfig();
    const { terms } = await mapReduceDocument(
      doc.chunks,
      createAnthropicTermsExtractor(),
      ai.mapGroupChars,
      ai.mapConcurrency,
    );
    return terms;
  },
  questions: async (doc: FullDocument) => {
    const { ai } = useRuntimeConfig();
    const { questions } = await mapReduceDocument(
      doc.chunks,
      createAnthropicQuestionGenerator(),
      ai.mapGroupChars,
      ai.mapConcurrency,
    );
    return questions;
  },
} satisfies Record<PrepPackKind, (doc: FullDocument) => Promise<unknown>>;

/**
 * Generate one prep-pack kind and persist it. Idempotent: `resolvePrepPack` returns the
 * stored value if the kind is already computed, else it loads the doc, computes, and saves.
 */
export async function generatePrepPack(documentId: string, kind: PrepPackKind): Promise<unknown> {
  const { value } = await resolvePrepPack<unknown>(documentId, kind, {
    getCache: getPrepPack,
    loadDoc: async (id) => {
      const doc = await fetchFullDocument(id);
      if (!doc.chunks?.length) {
        throw createError({ statusCode: 422, statusMessage: "document has no text yet" });
      }
      return doc;
    },
    compute: prepComputers[kind],
    saveCache: savePrepPack,
  });
  return value;
}

const KINDS = ["summary", "terms", "questions"] as const;

export interface PrepPackGenResult {
  document_id: string;
  generated: Record<PrepPackKind, "fulfilled" | "rejected">;
}

/**
 * Generate + persist all three kinds. Each kind is independent (`Promise.allSettled`), so
 * one kind failing never drops the others. `gen` is injectable for unit tests.
 */
export async function generateAllPrepPacks(
  documentId: string,
  gen: (id: string, kind: PrepPackKind) => Promise<unknown> = generatePrepPack,
): Promise<PrepPackGenResult> {
  const settled = await Promise.allSettled(KINDS.map((k) => gen(documentId, k)));
  const generated = Object.fromEntries(
    KINDS.map((k, i) => [k, settled[i].status]),
  ) as Record<PrepPackKind, "fulfilled" | "rejected">;
  return { document_id: documentId, generated };
}

/**
 * Authorize a server-to-server internal call. Empty configured key = open (local dev,
 * mirrors retrieval-api's api-key convention); otherwise the `X-API-Key` must match.
 */
export function assertInternalAuth(configuredKey: string, providedKey: string | undefined): void {
  if (configuredKey && providedKey !== configuredKey) {
    throw createError({ statusCode: 401, statusMessage: "unauthorized" });
  }
}
