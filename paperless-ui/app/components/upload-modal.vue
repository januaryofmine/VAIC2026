<script setup lang="ts">
const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ uploaded: [documentId: string] }>();

const file = ref<File | null>(null);
const uploading = ref(false);
const error = ref("");
const dragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

function setFile(f: File | null) {
  error.value = "";
  if (f && !isSupportedDoc(f.name)) {
    error.value = "Chỉ hỗ trợ file PDF hoặc Word (.docx)";
    return;
  }
  file.value = f;
}

function onDrop(e: DragEvent) {
  dragOver.value = false;
  setFile(e.dataTransfer?.files?.[0] ?? null);
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
    emit("uploaded", res.document_id);
    open.value = false;
  } catch (e: unknown) {
    const err = e as { data?: { statusMessage?: string; message?: string } };
    error.value = err?.data?.statusMessage || err?.data?.message || "Tải lên thất bại";
  } finally {
    uploading.value = false;
  }
}

watch(open, (v) => {
  if (!v) {
    file.value = null;
    error.value = "";
  }
});
</script>

<template>
  <UModal v-model:open="open" title="Tải tài liệu" :ui="{ content: 'max-w-lg' }">
    <template #body>
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx"
        class="hidden"
        data-testid="file-input"
        @change="(e) => setFile((e.target as HTMLInputElement).files?.[0] ?? null)"
      >

      <div
        class="flex flex-col items-center gap-2 rounded-xl border-[1.5px] border-dashed px-5 py-8 text-center transition-colors"
        :class="dragOver ? 'border-gold-500 bg-gold-50' : 'border-[var(--pl-border-strong)]'"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
      >
        <div class="grid size-12 place-items-center rounded-xl bg-navy-50 text-navy-800">
          <UIcon name="i-lucide-upload" class="text-2xl" />
        </div>
        <p v-if="file" class="font-semibold" data-testid="picked-name">{{ file.name }}</p>
        <template v-else>
          <p class="font-semibold">Kéo thả tài liệu vào đây</p>
          <p class="text-xs text-[var(--pl-text-3)]">hoặc</p>
        </template>
        <UButton color="neutral" variant="outline" size="sm" @click="fileInput?.click()">
          Chọn từ máy
        </UButton>
        <p class="mt-1 text-xs text-[var(--pl-text-3)]">PDF hoặc Word (.docx) · tối đa 25 MB</p>
      </div>

      <UAlert
        v-if="error"
        class="mt-4"
        color="error"
        variant="soft"
        icon="i-lucide-triangle-alert"
        :title="error"
        data-testid="upload-error"
      />
    </template>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton color="neutral" variant="ghost" @click="open = false">Huỷ</UButton>
        <UButton
          color="secondary"
          :loading="uploading"
          :disabled="!file || uploading"
          data-testid="upload-submit"
          @click="submit"
        >
          {{ uploading ? "Đang tải lên…" : "Tải lên" }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>
