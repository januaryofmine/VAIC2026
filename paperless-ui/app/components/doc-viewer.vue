<script setup lang="ts">
const props = defineProps<{
  documentId: string;
  docType?: string;
  filename?: string;
}>();

// PDFs render inline; DOCX (and anything else) falls back to a download link
// until DOCX→PDF conversion lands (Slice 15b).
const mode = computed(() => viewerModeFor(props.docType));
const fileUrl = computed(() => docFileUrl(props.documentId));

// Original blob may be missing (older docs ingested before blob storage) — the
// file proxy 404s, VuePdfEmbed emits loading-failed, and we show the same fallback.
const failed = ref(false);
const loaded = ref(false);
</script>

<template>
  <UCard :ui="{ body: 'p-0 sm:p-0' }" class="overflow-hidden" data-testid="doc-viewer">
    <ClientOnly>
      <div v-if="mode === 'pdf' && !failed" class="max-h-[calc(100vh-12rem)] overflow-auto bg-[var(--ui-bg-muted)]">
        <div v-if="!loaded" class="space-y-2 p-4" data-testid="doc-viewer-loading">
          <USkeleton class="h-4 w-1/3" />
          <USkeleton class="h-64 w-full" />
        </div>
        <VuePdfEmbed
          :source="fileUrl"
          text-layer
          class="pdf-embed"
          @loaded="loaded = true"
          @loading-failed="failed = true"
        />
      </div>

      <div
        v-else
        class="flex flex-col items-center gap-3 p-10 text-center"
        data-testid="doc-viewer-fallback"
      >
        <UIcon name="i-lucide-file-text" class="text-4xl text-[var(--ui-text-muted)]" />
        <p class="text-sm text-[var(--ui-text-muted)]">
          {{
            failed
              ? "Không mở được bản xem trước của tài liệu này."
              : "Xem trước chưa hỗ trợ định dạng này."
          }}
        </p>
        <UButton
          :to="fileUrl"
          external
          target="_blank"
          icon="i-lucide-download"
          variant="soft"
        >
          Tải tài liệu
        </UButton>
      </div>

      <template #fallback>
        <div class="space-y-2 p-4">
          <USkeleton class="h-4 w-1/3" />
          <USkeleton class="h-64 w-full" />
        </div>
      </template>
    </ClientOnly>
  </UCard>
</template>

<style scoped>
/* Keep pages centered with a little breathing room inside the scroll area. */
.pdf-embed :deep(.vue-pdf-embed__page) {
  margin: 0 auto 0.75rem;
  box-shadow: 0 1px 3px rgb(0 0 0 / 12%);
}
</style>
