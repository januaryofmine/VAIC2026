<script setup lang="ts">
import type { Term } from "~/types/prep-pack";

defineProps<{ terms: Term[] | null; pending: boolean; error: unknown }>();
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-book-open" class="text-primary" />
        <h2 class="font-semibold">Thuật ngữ</h2>
        <UBadge v-if="terms" color="neutral" variant="soft" data-testid="terms-count">
          {{ terms.length }}
        </UBadge>
      </div>
    </template>

    <div v-if="pending" class="space-y-2" data-testid="terms-loading">
      <USkeleton v-for="i in 4" :key="i" class="h-4 w-full" />
    </div>
    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      icon="i-lucide-triangle-alert"
      title="Không trích được thuật ngữ"
    />
    <dl v-else-if="terms" class="space-y-3 text-sm" data-testid="terms-content">
      <div v-for="(t, i) in terms" :key="i">
        <dt class="font-semibold text-primary">{{ t.term }}</dt>
        <dd class="text-[var(--ui-text-muted)]">{{ t.explanation }}</dd>
      </div>
    </dl>
  </UCard>
</template>
