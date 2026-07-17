export interface DocStatus {
  document_id: string;
  filename: string;
  doc_type: string;
  status: "pending" | "parsing" | "embedding" | "ready" | "failed";
  page_count: number | null;
  chunk_count: number;
}

/** Poll a document's ingestion status until it reaches ready/failed. Client-only. */
export function useDocStatus(documentId: string) {
  const info = ref<DocStatus | null>(null);
  const error = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;

  const isTerminal = (s?: string) => s === "ready" || s === "failed";

  async function poll() {
    try {
      const r = await $fetch<DocStatus>(`/api/documents/${documentId}/status`);
      info.value = r;
      if (!isTerminal(r.status)) timer = setTimeout(poll, 2000);
    } catch (e: unknown) {
      const err = e as { data?: { statusMessage?: string } };
      error.value = err?.data?.statusMessage || "Không lấy được trạng thái tài liệu";
    }
  }

  onMounted(poll);
  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer);
  });

  return {
    info,
    error,
    status: computed(() => info.value?.status ?? "pending"),
    ready: computed(() => info.value?.status === "ready"),
    failed: computed(() => info.value?.status === "failed"),
  };
}
