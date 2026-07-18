import { Chat } from "@ai-sdk/vue";
import type { UIMessage } from "ai";
import { DefaultChatTransport } from "ai";

/** Q&A chat for one document — streams answers from /api/chat scoped to document_id. */
export function useDocChat(documentId: string) {
  const chat = shallowRef<Chat<UIMessage> | null>(null);

  const makeChat = (initial: UIMessage[]) =>
    new Chat<UIMessage>({
      messages: initial,
      transport: new DefaultChatTransport({
        api: "/api/chat",
        body: { document_id: documentId },
      }),
      onError(error) {
        console.error("[chat] error:", error);
      },
    });

  if (import.meta.client) {
    // Render immediately, then hydrate with any saved history (Slice 14b).
    chat.value = makeChat([]);
    $fetch<{ messages: UIMessage[] }>(`/api/documents/${documentId}/chat/messages`)
      .then((res) => {
        if (res.messages?.length) chat.value = makeChat(res.messages);
      })
      .catch((e) => console.error("[chat] load history failed:", e));
  }

  const messages = computed(() => chat.value?.messages ?? []);
  const status = computed(() => chat.value?.status ?? "ready");

  function send(text: string) {
    chat.value?.sendMessage({ text });
  }

  return { messages, status, send };
}
