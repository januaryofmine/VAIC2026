<script setup lang="ts">
const { documents, loading, filters, apply, refresh } = useDocuments();
const uploadOpen = ref(false);

const typeOptions = [
  { label: "Tất cả", value: "all" }, // Reka UI forbids empty-string SelectItem values
  { label: "PDF", value: "pdf" },
  { label: "Word (.docx)", value: "docx" },
];

function onUploaded(documentId: string) {
  refresh();
  navigateTo(`/doc/${documentId}`);
}
</script>

<template>
  <div class="space-y-5">
    <!-- Page head -->
    <div class="flex flex-wrap items-end gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Tài liệu của tôi</h1>
        <p class="mt-1 text-sm text-[var(--pl-text-2)]">
          Tải lên tài liệu để hệ thống phân tích, hoặc mở lại tài liệu đã chuẩn bị.
        </p>
      </div>
      <div class="flex-1" />
      <UButton
        color="secondary"
        icon="i-lucide-plus"
        size="lg"
        data-testid="open-upload"
        @click="uploadOpen = true"
      >
        Tải tài liệu
      </UButton>
    </div>

    <!-- Filter bar -->
    <div class="filterbar">
      <div class="field grow">
        <label>Từ khoá</label>
        <UInput
          v-model="filters.q"
          placeholder="Tìm theo tên tài liệu…"
          icon="i-lucide-search"
          @keydown.enter="apply"
        />
      </div>
      <div class="field">
        <label>Loại</label>
        <USelect v-model="filters.type" :items="typeOptions" class="w-40" />
      </div>
      <div class="field">
        <label>Ngày tải lên</label>
        <div class="flex items-center gap-2">
          <UInput v-model="filters.date_from" type="date" />
          <span class="text-[var(--pl-text-3)]">–</span>
          <UInput v-model="filters.date_to" type="date" />
        </div>
      </div>
      <UButton color="secondary" icon="i-lucide-filter" @click="apply">Lọc</UButton>
    </div>

    <!-- Result count + table (data is client-fetched → render client-only) -->
    <ClientOnly>
      <p class="text-sm text-[var(--pl-text-2)]">
        <b class="text-[var(--pl-text)]">{{ documents.length }}</b> tài liệu
      </p>
      <DocumentsTable class="mt-3" :documents="documents" :loading="loading" />
      <template #fallback>
        <DocumentsTable :documents="[]" :loading="true" />
      </template>
    </ClientOnly>

    <UploadModal v-model:open="uploadOpen" @uploaded="onUploaded" />
  </div>
</template>

<style scoped>
.filterbar {
  background: #fff;
  border: 1px solid var(--pl-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(19, 30, 53, 0.04), 0 4px 14px rgba(19, 30, 53, 0.06);
  padding: 14px 16px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.field { display: flex; flex-direction: column; gap: 5px; }
.field.grow { flex: 1; min-width: 200px; }
.field label {
  font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
  text-transform: uppercase; color: var(--pl-text-3);
}
</style>
