<script setup lang="ts">
import type { JumpTarget } from "~/composables/useDocJump";

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

// Citation click-to-jump (Slice 15c): a chip in the right pane sets a JumpTarget;
// scroll to that page, flash it, and highlight the cited chunk's text-layer spans.
const viewerRoot = ref<HTMLElement | null>(null);
const { target } = useDocJump();

function highlightChunk(pageEl: HTMLElement, text: string) {
  const spans = pageEl.querySelectorAll<HTMLElement>(".textLayer span");
  spans.forEach((span) => {
    if (shouldHighlightSpan(text, span.textContent ?? "")) {
      span.classList.add("pl-cite-highlight");
    }
  });
}

function jumpAndHighlight(t: JumpTarget, attempt = 0) {
  const root = viewerRoot.value;
  if (!root) return;
  // vue-pdf-embed renders pages in order without a page-number attribute, so the
  // 1-indexed page is the Nth .vue-pdf-embed__page element.
  const pages = root.querySelectorAll<HTMLElement>(".vue-pdf-embed__page");
  const pageEl = pages[t.page - 1];
  if (!pageEl) {
    // Pages not rendered yet (large PDF) — retry a few times.
    if (attempt < 6) setTimeout(() => jumpAndHighlight(t, attempt + 1), 300);
    return;
  }
  pageEl.scrollIntoView({ behavior: "smooth", block: "start" });
  pageEl.classList.add("pl-flash");
  setTimeout(() => pageEl.classList.remove("pl-flash"), 1200);

  root.querySelectorAll(".pl-cite-highlight").forEach((el) => el.classList.remove("pl-cite-highlight"));
  if (!t.text) return;
  const hasSpans = pageEl.querySelector(".textLayer span");
  if (!hasSpans && attempt < 6) {
    setTimeout(() => jumpAndHighlight(t, attempt + 1), 300);
    return;
  }
  highlightChunk(pageEl, t.text);
}

watch(target, (t) => {
  if (t) jumpAndHighlight(t);
});
</script>

<template>
  <UCard :ui="{ body: 'p-0 sm:p-0' }" class="overflow-hidden" data-testid="doc-viewer">
    <ClientOnly>
      <div v-if="mode === 'pdf' && !failed" ref="viewerRoot" class="max-h-[calc(100vh-12rem)] overflow-auto bg-[var(--ui-bg-muted)]">
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

/* Citation jump: flash the target page gold, then highlight the cited chunk's
   text-layer spans (Slice 15c). Applied to child DOM → needs :deep. */
:deep(.vue-pdf-embed__page.pl-flash) {
  animation: pl-flash 1.2s ease-out;
}
@keyframes pl-flash {
  0%,
  100% {
    box-shadow: 0 1px 3px rgb(0 0 0 / 12%);
  }
  25% {
    box-shadow: 0 0 0 3px #c9a227;
  }
}
:deep(.textLayer .pl-cite-highlight) {
  background: rgb(201 162 39 / 38%);
  border-radius: 2px;
}
</style>
