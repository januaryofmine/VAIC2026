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
</script>

<template>
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
  </div>
</template>
