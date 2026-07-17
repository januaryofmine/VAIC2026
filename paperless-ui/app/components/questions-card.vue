<script setup lang="ts">
defineProps<{ questions: string[] | null; pending: boolean; error: unknown }>();
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-lightbulb" class="text-primary" />
        <h2 class="font-semibold">Câu hỏi gợi ý</h2>
        <UBadge v-if="questions" color="neutral" variant="soft" data-testid="questions-count">
          {{ questions.length }}
        </UBadge>
      </div>
    </template>

    <div v-if="pending" class="space-y-2" data-testid="questions-loading">
      <USkeleton v-for="i in 3" :key="i" class="h-4 w-full" />
    </div>
    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      icon="i-lucide-triangle-alert"
      title="Không tạo được câu hỏi"
    />
    <ol v-else-if="questions" class="list-decimal space-y-2 pl-5 text-sm" data-testid="questions-content">
      <li v-for="(q, i) in questions" :key="i">{{ q }}</li>
    </ol>
  </UCard>
</template>
