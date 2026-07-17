/** Client-side check mirroring the server's accepted upload types (UX pre-validation). */
export function isSupportedDoc(filename: string): boolean {
  const ext = filename.toLowerCase().split(".").pop();
  return ext === "pdf" || ext === "docx";
}
