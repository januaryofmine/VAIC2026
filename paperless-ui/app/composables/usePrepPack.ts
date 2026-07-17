import type { PrepSummary, Term } from "~/types/prep-pack";

/**
 * Kick off the three prep-pack endpoints in parallel (each ~30-50s of LLM work),
 * client-side, each exposing its own data/pending/error so sections fill in
 * independently as they resolve.
 */
export function usePrepPack(documentId: string) {
  const post = <T>(url: string, key: string) =>
    useLazyAsyncData<T>(
      key,
      () => $fetch<T>(url, { method: "POST", body: { document_id: documentId } }),
      { server: false },
    );

  const s = post<{ filename: string; summary: PrepSummary }>(
    "/api/summarize",
    `summary-${documentId}`,
  );
  const t = post<{ terms: Term[] }>("/api/terms", `terms-${documentId}`);
  const q = post<{ questions: string[] }>("/api/questions", `questions-${documentId}`);

  return {
    filename: computed(() => s.data.value?.filename ?? ""),
    summary: s.data,
    summaryPending: s.pending,
    summaryError: s.error,
    terms: t.data,
    termsPending: t.pending,
    termsError: t.error,
    questions: q.data,
    questionsPending: q.pending,
    questionsError: q.error,
  };
}
