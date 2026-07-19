// The model sometimes bakes its own "1. "/"2) " prefix into each question string;
// questions-card.vue's <ol> already numbers items, so strip it to avoid "1. 1. ..." doubling.
export function stripLeadingEnumeration(text: string): string {
  return text.replace(/^\s*\d+[.)]\s*/, "");
}
