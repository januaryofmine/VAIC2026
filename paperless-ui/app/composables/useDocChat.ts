import { Chat } from "@ai-sdk/vue";
import type { UIMessage } from "ai";
import { DefaultChatTransport } from "ai";

/** Q&A chat for one document — streams answers from /api/chat scoped to document_id. */
export function useDocChat(documentId: string) {
  const chat = shallowRef<Chat<UIMessage> | null>(null);

  if (import.meta.client) {
    chat.value = new Chat<UIMessage>({
      transport: new DefaultChatTransport({
        api: "/api/chat",
        body: { document_id: documentId },
      }),
      onError(error) {
        console.error("[chat] error:", error);
      },
    });
  }

  const messages = computed(() => chat.value?.messages ?? []);
  const status = computed(() => chat.value?.status ?? "ready");

  function send(text: string) {
    chat.value?.sendMessage({ text });
  }

  return { messages, status, send };
}
