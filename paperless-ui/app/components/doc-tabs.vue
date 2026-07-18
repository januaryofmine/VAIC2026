<script setup lang="ts">
const props = defineProps<{ documentId: string }>();

const {
  summary,
  summaryPending,
  summaryError,
  terms,
  termsPending,
  termsError,
  questions,
  questionsPending,
  questionsError,
} = usePrepPack(props.documentId);

// Tab labels carry the live counts once the prep-pack sections resolve.
const items = computed(() =>
  buildDocTabs({
    terms: terms.value?.terms?.length ?? null,
    questions: questions.value?.questions?.length ?? null,
  }).map((t) => ({ ...t, slot: t.value })),
);
</script>

<template>
  <UTabs
    :items="items"
    default-value="summary"
    variant="link"
    :ui="{ list: 'sticky top-0 z-10 bg-[var(--ui-bg)]' }"
    data-testid="doc-tabs"
  >
    <template #summary>
      <SummaryCard
        :summary="summary?.summary ?? null"
        :pending="summaryPending"
        :error="summaryError"
      />
    </template>
    <template #terms>
      <TermsCard :terms="terms?.terms ?? null" :pending="termsPending" :error="termsError" />
    </template>
    <template #questions>
      <QuestionsCard
        :questions="questions?.questions ?? null"
        :pending="questionsPending"
        :error="questionsError"
      />
    </template>
    <template #chat>
      <ChatPanel :document-id="documentId" />
    </template>
  </UTabs>
</template>
