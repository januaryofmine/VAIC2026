<script setup lang="ts">
const route = useRoute();
const documentId = route.params.id as string;

const {
  filename,
  summary,
  summaryPending,
  summaryError,
  terms,
  termsPending,
  termsError,
  questions,
  questionsPending,
  questionsError,
} = usePrepPack(documentId);
</script>

<template>
  <div class="space-y-4">
    <UButton to="/" icon="i-lucide-arrow-left" variant="ghost" size="sm">Tải tài liệu khác</UButton>

    <div>
      <h1 class="text-lg font-semibold" data-testid="doc-filename">
        {{ filename || "Đang xử lý tài liệu…" }}
      </h1>
      <p class="font-mono text-xs text-[var(--ui-text-muted)]">{{ documentId }}</p>
    </div>

    <!-- Prep-pack data is fetched client-side only (server: false); render it
         client-only to avoid an SSR/client hydration mismatch on the pending state. -->
    <ClientOnly>
      <div class="space-y-4">
        <SummaryCard
          :summary="summary?.summary ?? null"
          :pending="summaryPending"
          :error="summaryError"
        />
        <TermsCard :terms="terms?.terms ?? null" :pending="termsPending" :error="termsError" />
        <QuestionsCard
          :questions="questions?.questions ?? null"
          :pending="questionsPending"
          :error="questionsError"
        />
        <ChatPanel :document-id="documentId" />
      </div>
      <template #fallback>
        <p class="text-sm text-[var(--ui-text-muted)]">Đang tải…</p>
      </template>
    </ClientOnly>
  </div>
</template>
