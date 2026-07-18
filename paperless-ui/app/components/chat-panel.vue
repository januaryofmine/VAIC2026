<script setup lang="ts">
import type { UIMessage } from "ai";

import type { Source } from "~/utils/citations";

const props = defineProps<{ documentId: string }>();

const { messages, status, send } = useDocChat(props.documentId);
const { requestJump } = useDocJump();
const input = ref("");
const busy = computed(() => status.value === "submitted" || status.value === "streaming");

function onSend() {
  const text = input.value.trim();
  if (!text || busy.value) return;
  send(text);
  input.value = "";
}

function textOf(m: UIMessage): string {
  return m.parts
    .filter((p) => p.type === "text")
    .map((p) => (p as { text: string }).text)
    .join("");
}

function sourcesOf(m: UIMessage): Source[] {
  const meta = m.metadata as { sources?: Source[] } | undefined;
  return dedupeSources(meta?.sources ?? []);
}
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-messages-square" class="text-primary" />
        <h2 class="font-semibold">Hỏi đáp tài liệu</h2>
      </div>
    </template>

    <div class="space-y-3">
      <p v-if="messages.length === 0" class="text-sm text-[var(--ui-text-muted)]">
        Đặt câu hỏi về tài liệu.
      </p>

      <div v-for="(m, i) in messages" :key="m.id ?? i" data-testid="chat-message">
        <div :class="m.role === 'user' ? 'text-right' : ''">
          <div
            :class="[
              'inline-block max-w-[85%] whitespace-pre-line rounded-lg px-3 py-2 text-sm',
              m.role === 'user'
                ? 'bg-primary text-inverted'
                : 'bg-[var(--ui-bg-elevated)]',
            ]"
          >
            {{ textOf(m) }}
          </div>
          <div
            v-if="m.role === 'assistant' && sourcesOf(m).length"
            class="mt-1 flex flex-wrap gap-1"
            data-testid="chat-sources"
          >
            <UBadge
              v-for="(s, j) in sourcesOf(m)"
              :key="j"
              color="neutral"
              variant="soft"
              size="sm"
              icon="i-lucide-quote"
              :class="s.page != null ? 'cursor-pointer hover:bg-[var(--ui-bg-accented)]' : ''"
              :title="s.page != null ? 'Xem trong tài liệu' : undefined"
              @click="s.page != null && requestJump(s)"
            >
              {{ citationLabel(s) }}
            </UBadge>
          </div>
        </div>
      </div>

      <UAlert
        v-if="status === 'error'"
        color="error"
        variant="soft"
        icon="i-lucide-triangle-alert"
        title="Không trả lời được"
        description="Có lỗi khi xử lý câu hỏi. Vui lòng thử lại."
        data-testid="chat-error"
      />
    </div>

    <template #footer>
      <form class="flex gap-2" @submit.prevent="onSend">
        <UInput
          v-model="input"
          placeholder="Hỏi về nội dung tài liệu…"
          class="flex-1"
          :disabled="busy"
          data-testid="chat-input"
        />
        <UButton
          type="submit"
          icon="i-lucide-send"
          :loading="busy"
          :disabled="!input.trim() || busy"
          data-testid="chat-send"
        >
          Gửi
        </UButton>
      </form>
    </template>
  </UCard>
</template>
