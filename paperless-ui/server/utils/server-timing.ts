import { setResponseHeader, type H3Event } from "h3";

/** One `Server-Timing` metric: a per-layer duration surfaced in the browser's
 * Network → Timing panel. Only names + millisecond numbers are sent — never any
 * request/document content — so this is safe for the legal-document data. */
export interface ServerTimingMetric {
  name: string;
  dur: number;
  desc?: string;
}

/** Reduce a name to a Server-Timing token: header grammar forbids spaces and the
 * `;`/`,` delimiters, so replace any run of unsafe chars with `-`. */
function toToken(name: string): string {
  const token = name.replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  return token || "x";
}

function quoteDesc(desc: string): string {
  return `"${desc.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

/** Build a `Server-Timing` header value from metrics (pure — unit-tested). Metrics
 * with a non-finite duration are dropped; an empty list yields an empty string. */
export function formatServerTiming(metrics: ServerTimingMetric[]): string {
  return metrics
    .filter((m) => m && typeof m.dur === "number" && Number.isFinite(m.dur))
    .map((m) => {
      const base = `${toToken(m.name)};dur=${round1(m.dur)}`;
      return m.desc ? `${base};desc=${quoteDesc(m.desc)}` : base;
    })
    .join(", ");
}

/** Set the `Server-Timing` response header (no-op when there is nothing to report).
 * Best-effort observability: wrapped so it can NEVER throw and break the response. */
export function setServerTiming(event: H3Event, metrics: ServerTimingMetric[]): void {
  try {
    const value = formatServerTiming(metrics);
    if (value) setResponseHeader(event, "Server-Timing", value);
  } catch {
    // Observability must never affect the response — swallow any header error.
  }
}
