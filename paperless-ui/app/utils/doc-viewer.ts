export type ViewerMode = "pdf" | "unsupported";

/**
 * How the left doc pane should render a document. Only PDFs get the inline
 * PDF.js viewer today; DOCX (and anything else) falls back to a download link
 * until DOCX→PDF conversion lands (Slice 15b).
 */
export function viewerModeFor(docType?: string): ViewerMode {
  return docType?.toLowerCase() === "pdf" ? "pdf" : "unsupported";
}

/** URL of the original file blob proxy for a document. */
export function docFileUrl(documentId: string): string {
  return `/api/documents/${documentId}/file`;
}
