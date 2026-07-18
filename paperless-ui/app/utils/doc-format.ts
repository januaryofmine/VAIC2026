// Display helpers for the documents list (Slice 18).

export type StatusKind = "ok" | "warn" | "err";

/** Map an ingestion status to a Vietnamese label + a semantic kind for the badge. */
export function statusMeta(status: string): { label: string; kind: StatusKind } {
  if (status === "ready") return { label: "Sẵn sàng", kind: "ok" };
  if (status === "failed") return { label: "Lỗi xử lý", kind: "err" };
  return { label: "Đang xử lý", kind: "warn" }; // pending | parsing | embedding
}

export function isReady(status: string): boolean {
  return status === "ready";
}

export function docTypeLabel(docType: string): string {
  return docType === "docx" ? "Word" : "PDF";
}

function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/**
 * Format the server's ISO upload time as "Hôm nay, HH:MM" / "Hôm qua, HH:MM" / "DD/MM/YYYY, HH:MM".
 * String-based on the server's stated local date so it's timezone-stable.
 */
export function formatUploadedAt(iso: string, now: Date = new Date()): string {
  const datePart = iso.slice(0, 10); // YYYY-MM-DD
  const timePart = iso.slice(11, 16); // HH:MM
  if (datePart === ymd(now)) return `Hôm nay, ${timePart}`;
  if (datePart === ymd(new Date(now.getTime() - 86_400_000))) return `Hôm qua, ${timePart}`;
  const [y, m, d] = datePart.split("-");
  return `${d}/${m}/${y}, ${timePart}`;
}
