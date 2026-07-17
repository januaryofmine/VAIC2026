<script setup lang="ts">
const route = useRoute();
const documentId = route.params.id as string;
</script>

<template>
  <div class="space-y-4">
    <UButton to="/" icon="i-lucide-arrow-left" variant="ghost" size="sm">Tải tài liệu khác</UButton>
    <UCard>
      <p class="text-sm text-[var(--ui-text-muted)]">Tài liệu</p>
      <p class="font-mono text-sm" data-testid="document-id">{{ documentId }}</p>
      <p class="mt-2 text-[var(--ui-text-muted)]">
        Bản tóm tắt, thuật ngữ và Q&A sẽ hiển thị ở đây (Slice 6b–6c).
      </p>
    </UCard>
  </div>
</template>
