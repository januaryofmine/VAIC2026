<script setup lang="ts">
import type { PrepSummary } from "~/types/prep-pack";

defineProps<{ summary: PrepSummary | null; pending: boolean; error: unknown }>();
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-file-text" class="text-primary" />
        <h2 class="font-semibold">Tóm tắt</h2>
      </div>
    </template>

    <div v-if="pending" class="space-y-2" data-testid="summary-loading">
      <USkeleton class="h-4 w-full" />
      <USkeleton class="h-4 w-5/6" />
      <USkeleton class="h-4 w-4/6" />
    </div>
    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      icon="i-lucide-triangle-alert"
      title="Không tạo được tóm tắt"
    />
    <div v-else-if="summary" class="space-y-4 text-sm" data-testid="summary-content">
      <div>
        <p class="font-medium text-[var(--ui-text-muted)]">Bối cảnh</p>
        <p>{{ summary.context }}</p>
      </div>
      <div>
        <p class="font-medium text-[var(--ui-text-muted)]">Nội dung chính</p>
        <p class="whitespace-pre-line">{{ summary.main_content }}</p>
      </div>
      <div>
        <p class="font-medium text-[var(--ui-text-muted)]">Điểm cần quyết định</p>
        <ul class="list-disc space-y-1 pl-5">
          <li v-for="(d, i) in summary.decision_points" :key="i">{{ d }}</li>
        </ul>
      </div>
      <div>
        <p class="font-medium text-[var(--ui-text-muted)]">Tác động</p>
        <p>{{ summary.impact }}</p>
      </div>
    </div>
  </UCard>
</template>
