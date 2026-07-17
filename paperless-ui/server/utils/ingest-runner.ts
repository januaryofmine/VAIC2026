import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

/** Map an upload filename to its supported document type, or null if unsupported. */
export function detectDocType(filename: string): "pdf" | "docx" | null {
  const ext = filename.toLowerCase().split(".").pop();
  return ext === "pdf" || ext === "docx" ? ext : null;
}

/** Pull the document_id that ingest.py prints on success. */
export function parseDocumentId(stdout: string): string | null {
  const m = stdout.match(/document_id=([0-9a-fA-F-]{36})/);
  return m ? m[1] : null;
}

/**
 * Run the Python ingestion pipeline (parse → chunk → embed → insert) on a saved
 * file, via subprocess. execFile (not a shell) so the path can't inject commands.
 */
export async function runIngestion(
  filePath: string,
  ragPipelineDir: string,
  timeoutMs = 300_000,
): Promise<string> {
  const { stdout } = await execFileAsync(
    "uv",
    ["run", "python", "ingest.py", filePath],
    {
      cwd: ragPipelineDir,
      env: process.env, // inherits DATABASE_URL etc.
      timeout: timeoutMs,
      maxBuffer: 10 * 1024 * 1024,
    },
  );
  const documentId = parseDocumentId(stdout);
  if (!documentId) {
    throw new Error(`ingestion returned no document_id. tail: ${stdout.slice(-400)}`);
  }
  return documentId;
}
