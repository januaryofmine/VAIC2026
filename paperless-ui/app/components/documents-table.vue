<script setup lang="ts">
import type { DocItem } from "~/composables/useDocuments";

defineProps<{ documents: DocItem[]; loading: boolean }>();

const kindClass: Record<string, string> = { ok: "st-ok", warn: "st-warn", err: "st-err" };

function open(doc: DocItem) {
  if (isReady(doc.status)) navigateTo(`/doc/${doc.document_id}`);
}
</script>

<template>
  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th>Tên tài liệu</th>
          <th>Loại</th>
          <th>Trạng thái</th>
          <th>Số đoạn</th>
          <th>Ngày tải lên</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading">
          <td colspan="6" class="empty">Đang tải…</td>
        </tr>
        <tr v-else-if="documents.length === 0">
          <td colspan="6" class="empty" data-testid="docs-empty">
            Chưa có tài liệu nào. Bấm “Tải tài liệu” để bắt đầu.
          </td>
        </tr>
        <tr
          v-for="doc in documents"
          v-else
          :key="doc.document_id"
          :class="{ clickable: isReady(doc.status) }"
          data-testid="doc-row"
          @click="open(doc)"
        >
          <td>
            <div class="name-cell">
              <div class="filetype" :class="doc.doc_type === 'docx' ? 'ft-docx' : 'ft-pdf'">
                {{ doc.doc_type === "docx" ? "DOCX" : "PDF" }}
              </div>
              <span class="name-text">{{ doc.filename }}</span>
            </div>
          </td>
          <td class="muted">
            {{ docTypeLabel(doc.doc_type)
            }}<template v-if="doc.page_count"> · {{ doc.page_count }} tr</template>
          </td>
          <td>
            <span class="status" :class="kindClass[statusMeta(doc.status).kind]">
              <span class="dot" />{{ statusMeta(doc.status).label }}
            </span>
          </td>
          <td class="muted num">{{ doc.chunk_count || "—" }}</td>
          <td class="muted">{{ formatUploadedAt(doc.uploaded_at) }}</td>
          <td class="text-right" @click.stop>
            <UButton
              v-if="isReady(doc.status)"
              :to="`/doc/${doc.document_id}`"
              variant="ghost"
              color="primary"
              size="xs"
              trailing-icon="i-lucide-arrow-right"
            >
              Mở
            </UButton>
            <span v-else-if="doc.status === 'failed'" class="text-xs text-[var(--pl-err)]">
              Thử lại
            </span>
            <span v-else class="text-xs text-[var(--pl-text-3)]">…</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.tbl-wrap {
  background: #fff;
  border: 1px solid var(--pl-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(19, 30, 53, 0.04), 0 4px 14px rgba(19, 30, 53, 0.06);
  overflow-x: auto;
}
table { width: 100%; border-collapse: collapse; min-width: 720px; }
thead th {
  text-align: left; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  text-transform: uppercase; color: var(--pl-text-3); padding: 13px 16px;
  border-bottom: 1px solid var(--pl-border); white-space: nowrap;
}
tbody td { padding: 14px 16px; border-bottom: 1px solid #eef1f5; vertical-align: middle; font-size: 14px; }
tbody tr:last-child td { border-bottom: none; }
tbody tr.clickable { cursor: pointer; }
tbody tr.clickable:hover { background: #f8fafc; }
.empty { text-align: center; color: var(--pl-text-3); padding: 34px 16px; }
.name-cell { display: flex; align-items: center; gap: 12px; min-width: 260px; }
.filetype {
  width: 34px; height: 34px; border-radius: 8px; flex-shrink: 0; display: grid;
  place-items: center; font-size: 9px; font-weight: 700; letter-spacing: 0.3px;
}
.ft-pdf { background: #f4ecec; color: #b5463c; }
.ft-docx { background: #e9eef7; color: #315b9c; }
.name-text {
  font-weight: 600; color: var(--pl-text); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; max-width: 360px;
}
.muted { color: var(--pl-text-2); white-space: nowrap; }
.num { font-variant-numeric: tabular-nums; }
.status {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px;
  font-weight: 600; padding: 4px 10px; border-radius: 999px; white-space: nowrap;
}
.status .dot { width: 7px; height: 7px; border-radius: 50%; }
.st-ok { color: var(--pl-ok); background: var(--pl-ok-bg); }
.st-ok .dot { background: var(--pl-ok); }
.st-warn { color: var(--pl-warn); background: var(--pl-warn-bg); }
.st-warn .dot { background: var(--pl-warn); animation: pl-pulse 1.4s ease-in-out infinite; }
.st-err { color: var(--pl-err); background: var(--pl-err-bg); }
.st-err .dot { background: var(--pl-err); }
@keyframes pl-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
@media (prefers-reduced-motion: reduce) { .st-warn .dot { animation: none; } }
</style>
