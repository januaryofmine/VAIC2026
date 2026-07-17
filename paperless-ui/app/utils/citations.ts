export interface Source {
  position?: number;
  page: number | null;
  section: string | null;
}

/** Human label for a citation chip, e.g. "trang 3, Điều 1" or "Điều 5". */
export function citationLabel(s: Source): string {
  return (
    [s.page != null ? `trang ${s.page}` : null, s.section].filter(Boolean).join(", ") ||
    "nguồn"
  );
}

/** Collapse sources that share the same label (top-k often repeats a page). */
export function dedupeSources(sources: Source[]): Source[] {
  const seen = new Set<string>();
  const out: Source[] = [];
  for (const s of sources) {
    const key = citationLabel(s);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(s);
    }
  }
  return out;
}
