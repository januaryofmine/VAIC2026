<script setup lang="ts">
const fileInput = ref<HTMLInputElement | null>(null);
const file = ref<File | null>(null);
const uploading = ref(false);
const error = ref("");

const selectedName = computed(() => file.value?.name ?? "");

function pick() {
  fileInput.value?.click();
}

function onChange(e: Event) {
  const picked = (e.target as HTMLInputElement).files?.[0] ?? null;
  error.value = "";
  if (picked && !isSupportedDoc(picked.name)) {
    error.value = "Chỉ hỗ trợ file PDF hoặc Word (.docx)";
    file.value = null;
    return;
  }
  file.value = picked;
}

async function submit() {
  if (!file.value) return;
  uploading.value = true;
  error.value = "";
  try {
    const form = new FormData();
    form.append("file", file.value);
    const res = await $fetch<{ document_id: string }>("/api/upload", {
      method: "POST",
      body: form,
    });
    await navigateTo(`/doc/${res.document_id}`);
  } catch (e: unknown) {
    const err = e as { data?: { statusMessage?: string; message?: string } };
    error.value = err?.data?.statusMessage || err?.data?.message || "Tải lên thất bại";
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <UCard>
    <template #header>
      <h1 class="text-lg font-semibold">Tải tài liệu họp</h1>
      <p class="text-sm text-[var(--ui-text-muted)]">
        PDF hoặc Word (.docx) — AI sẽ tóm tắt, giải thích thuật ngữ và gợi ý câu hỏi.
      </p>
    </template>

    <div class="space-y-4">
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx"
        class="hidden"
        @change="onChange"
      >
      <div class="flex items-center gap-3">
        <UButton icon="i-lucide-upload" variant="soft" @click="pick">Chọn file</UButton>
        <span class="text-sm text-[var(--ui-text-muted)]" data-testid="selected-name">
          {{ selectedName || "Chưa chọn file" }}
        </span>
      </div>
      <UAlert
        v-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-triangle-alert"
        :title="error"
        data-testid="upload-error"
      />
    </div>

    <template #footer>
      <UButton
        :loading="uploading"
        :disabled="!file || uploading"
        icon="i-lucide-sparkles"
        data-testid="upload-submit"
        @click="submit"
      >
        {{ uploading ? "Đang phân tích..." : "Tải lên & phân tích" }}
      </UButton>
    </template>
  </UCard>
</template>
