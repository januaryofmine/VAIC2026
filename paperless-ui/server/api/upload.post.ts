import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";

export default defineEventHandler(async (event) => {
  const form = await readMultipartFormData(event);
  const filePart = form?.find((p) => p.name === "file" && p.filename);
  if (!filePart || !filePart.filename) {
    throw createError({ statusCode: 400, statusMessage: "file field is required" });
  }

  const docType = detectDocType(filePart.filename);
  if (!docType) {
    throw createError({
      statusCode: 400,
      statusMessage: "unsupported file type (only .pdf or .docx)",
    });
  }

  const config = useRuntimeConfig();
  const maxBytes = config.ingest.maxFileMb * 1024 * 1024;
  if (filePart.data.length > maxBytes) {
    throw createError({
      statusCode: 413,
      statusMessage: `file too large (max ${config.ingest.maxFileMb}MB)`,
    });
  }

  // Save under a unique temp dir keeping the ORIGINAL name (basename strips any
  // path traversal). The dir is removed only when the background ingest exits.
  const safeName = basename(filePart.filename);
  const dir = await mkdtemp(join(tmpdir(), "paperless-"));
  const tmpPath = join(dir, safeName);
  await writeFile(tmpPath, filePart.data);

  const ragPipelineDir = resolve(process.cwd(), config.ingest.ragPipelineDir);
  try {
    // Resolves as soon as the document row exists (id emitted early); ingestion
    // continues in the background and updates documents.status. Cleanup on exit.
    const documentId = await startIngestion(tmpPath, ragPipelineDir, () => {
      void rm(dir, { recursive: true, force: true });
    });
    return { document_id: documentId, filename: safeName, doc_type: docType, status: "processing" };
  } catch (e) {
    void rm(dir, { recursive: true, force: true });
    throw createError({ statusCode: 500, statusMessage: "failed to start ingestion" });
  }
});
