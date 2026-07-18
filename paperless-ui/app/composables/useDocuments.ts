export interface DocItem {
  document_id: string;
  filename: string;
  doc_type: string;
  status: string;
  page_count: number | null;
  chunk_count: number;
  size_bytes: number | null;
  uploaded_at: string;
}

interface DocListResponse {
  documents: DocItem[];
}

/** "Tài liệu của tôi": fetch the user's documents; filters apply on demand (Lọc button). */
export function useDocuments() {
  const filters = reactive({ q: "", type: "all", date_from: "", date_to: "" });

  // Empty / "all" values are dropped so we don't send meaningless filters upstream.
  const query = computed(() => ({
    q: filters.q || undefined,
    type: filters.type && filters.type !== "all" ? filters.type : undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  }));

  const { data, status, refresh } = useFetch<DocListResponse>("/api/documents", {
    query,
    watch: false, // apply filters explicitly, not on every keystroke
    server: false, // client-only: avoids SSR session/hydration complexity
    default: () => ({ documents: [] }),
  });

  const documents = computed(() => data.value?.documents ?? []);
  const loading = computed(() => status.value === "pending");

  return { documents, loading, filters, apply: () => refresh(), refresh };
}
