import type { InjectionKey, Ref } from "vue";

import type { Source } from "~/utils/citations";

/** A request to jump the doc viewer to a citation's page and highlight its chunk. */
export interface JumpTarget {
  page: number;
  text?: string;
  /** Bumped on every request so re-clicking the same citation still re-triggers. */
  token: number;
}

interface DocJump {
  target: Ref<JumpTarget | null>;
  requestJump: (source: Source) => void;
}

const KEY: InjectionKey<DocJump> = Symbol("docJump");

/**
 * Create the citation → viewer channel and provide it. Call once in the doc page
 * so the left pane (viewer) and right pane (chat chips) share one jump state.
 */
export function provideDocJump(): DocJump {
  const target = ref<JumpTarget | null>(null);
  let token = 0;
  const requestJump = (source: Source) => {
    if (source.page == null) return; // DOCX / no page → nothing to jump to
    target.value = { page: source.page, text: source.text, token: ++token };
  };
  const channel: DocJump = { target, requestJump };
  provide(KEY, channel);
  return channel;
}

/** Consume the channel from a child of the doc page (viewer or chat chip). */
export function useDocJump(): DocJump {
  const channel = inject(KEY, null);
  if (!channel) {
    // Rendered outside a doc page (shouldn't happen) — no-op fallback.
    return { target: ref(null), requestJump: () => {} };
  }
  return channel;
}
