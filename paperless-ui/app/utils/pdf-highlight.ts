// Locate a cited chunk's text inside a rendered PDF page's text layer, the way
// kotaemon does it (assets/js/pdf_viewer.js): never trust LLM offsets — fuzzy-match
// the source text against each PDF.js text-layer span and highlight the matches.

/** NFC-normalize + lowercase so Vietnamese composed/decomposed diacritics compare equal. */
export function normalizeForMatch(s: string): string {
  return s.normalize("NFC").toLowerCase();
}

/**
 * Longest-common-substring length of a and b, divided by the shorter length —
 * a substring of the other scores ~1. Port of kotaemon's `matchRatio` (LCS DP).
 * Inputs should already be normalized. Empty input → 0.
 */
export function matchRatio(a: string, b: string): number {
  const n = a.length;
  const m = b.length;
  if (n === 0 || m === 0) return 0;

  let prev = new Array<number>(m + 1).fill(0);
  let longest = 0;
  for (let i = 1; i <= n; i++) {
    const curr = new Array<number>(m + 1).fill(0);
    for (let j = 1; j <= m; j++) {
      if (a[i - 1] === b[j - 1]) {
        curr[j] = prev[j - 1] + 1;
        if (curr[j] > longest) longest = curr[j];
      }
    }
    prev = curr;
  }
  return longest / Math.min(n, m);
}

/**
 * Should this PDF text-layer span be highlighted as part of the cited chunk?
 * Skips tiny spans (noise) and requires the span's text to fuzzy-match the chunk
 * above the threshold — so a span that is a line of the chunk lights up, an
 * unrelated span does not.
 */
export function shouldHighlightSpan(
  chunkText: string,
  spanText: string,
  threshold = 0.5,
): boolean {
  if (spanText.trim().length <= 4) return false;
  return matchRatio(normalizeForMatch(chunkText), normalizeForMatch(spanText)) > threshold;
}
