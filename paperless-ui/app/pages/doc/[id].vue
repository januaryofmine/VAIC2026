<script setup lang="ts">
const route = useRoute();
const documentId = route.params.id as string;

const { info, error, status, ready, failed } = useDocStatus(documentId);

const statusLabel = computed(
  () =>
    ({
      pending: "Đang chờ xử lý…",
      parsing: "Đang đọc tài liệu…",
      embedding: "Đang tạo chỉ mục (embedding)…",
    })[status.value] || "Đang xử lý…",
);
</script>

<template>
  <div class="space-y-4">
    <UButton to="/" icon="i-lucide-arrow-left" variant="ghost" size="sm">Tải tài liệu khác</UButton>

    <div>
      <h1 class="text-lg font-semibold" data-testid="doc-filename">
        {{ info?.filename || "Tài liệu" }}
      </h1>
      <p class="font-mono text-xs text-[var(--ui-text-muted)]">{{ documentId }}</p>
    </div>

    <UAlert
      v-if="failed"
      color="error"
      variant="soft"
      icon="i-lucide-triangle-alert"
      title="Xử lý tài liệu thất bại"
      description="Không đọc hoặc tạo chỉ mục được tài liệu. Vui lòng thử tải lại."
      data-testid="doc-failed"
    />
    <UAlert v-else-if="error" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="error" />

    <UCard v-else-if="!ready" data-testid="doc-processing">
      <div class="flex items-center gap-3">
        <UIcon name="i-lucide-loader-circle" class="animate-spin text-xl text-primary" />
        <div>
          <p class="font-medium">{{ statusLabel }}</p>
          <p class="text-sm text-[var(--ui-text-muted)]">
            Bản tóm tắt, thuật ngữ và Q&A sẽ tự hiển thị khi xong.
          </p>
        </div>
      </div>
    </UCard>

    <ClientOnly v-else>
      <div class="space-y-4" data-testid="doc-ready">
        <PrepPack :document-id="documentId" />
        <ChatPanel :document-id="documentId" />
      </div>
    </ClientOnly>
  </div>
</template>
