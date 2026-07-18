import { spawn } from "node:child_process";

/** Map an upload filename to its supported document type, or null if unsupported. */
export function detectDocType(filename: string): "pdf" | "docx" | null {
  const ext = filename.toLowerCase().split(".").pop();
  return ext === "pdf" || ext === "docx" ? ext : null;
}

/** Pull the document_id that ingest.py prints (emitted early, before embedding). */
export function parseDocumentId(stdout: string): string | null {
  const m = stdout.match(/document_id=([0-9a-fA-F-]{36})/);
  return m ? m[1] : null;
}

/**
 * Start ingestion as a background subprocess and resolve as soon as ingest.py
 * prints the document_id (which it does BEFORE the slow embedding step). The
 * child keeps running (parse→embed→insert, updating documents.status); `onDone`
 * fires when it exits so the caller can clean up the temp file.
 */
export function startIngestion(
  filePath: string,
  ragPipelineDir: string,
  onDone?: () => void,
  earlyTimeoutMs = 60_000,
  userId?: string,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const args = ["run", "python", "ingest.py", filePath];
    if (userId) args.push("--user-id", userId); // owner scope (Slice 18)
    const child = spawn("uv", args, {
      cwd: ragPipelineDir,
      env: process.env,
    });
    let out = "";
    let err = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        child.kill();
        reject(new Error("timeout waiting for document_id"));
      }
    }, earlyTimeoutMs);

    child.stdout.on("data", (d) => {
      out += d.toString();
      const id = parseDocumentId(out);
      if (id && !settled) {
        settled = true;
        clearTimeout(timer);
        resolve(id); // return early; embedding continues in the background
      }
    });
    child.stderr.on("data", (d) => {
      err += d.toString();
    });
    child.on("error", (e) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        reject(e);
      }
    });
    child.on("exit", (code) => {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        reject(new Error(`ingest exited ${code} before document_id. ${err.slice(-400)}`));
      }
      onDone?.();
    });
  });
}
