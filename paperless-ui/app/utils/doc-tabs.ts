export interface DocTab {
  value: string;
  label: string;
  icon: string;
}

/** Counts shown next to the prep-pack tab labels (null while still loading). */
export interface DocTabCounts {
  terms: number | null;
  questions: number | null;
}

const withCount = (label: string, count: number | null) =>
  count != null ? `${label} ${count}` : label;

/**
 * The four tabs of the doc-reading right pane, in fixed order:
 * summary · terms · questions · chat. Terms/questions show their count once known.
 */
export function buildDocTabs(counts: DocTabCounts): DocTab[] {
  return [
    { value: "summary", label: "Tóm tắt", icon: "i-lucide-file-text" },
    { value: "terms", label: withCount("Thuật ngữ", counts.terms), icon: "i-lucide-book-open" },
    {
      value: "questions",
      label: withCount("Câu hỏi", counts.questions),
      icon: "i-lucide-lightbulb",
    },
    { value: "chat", label: "Hỏi đáp", icon: "i-lucide-messages-square" },
  ];
}
