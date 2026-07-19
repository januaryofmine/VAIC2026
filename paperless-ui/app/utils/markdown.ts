function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderMarkdown(text: string): string {
  let html = escapeHtml(text ?? "");

  // `inline code`
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // **đậm** hoặc __đậm__ (xử lý trước để không đụng cú pháp nghiêng)
  html = html.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/__([^_]+?)__/g, "<strong>$1</strong>");

  // *nghiêng* hoặc _nghiêng_ (tránh dính dấu * còn sót)
  html = html.replace(/(^|[^*])\*([^*\n]+?)\*/g, "$1<em>$2</em>");
  html = html.replace(/(^|[^_\w])_([^_\n]+?)_/g, "$1<em>$2</em>");

  // xuống dòng
  html = html.replace(/\n/g, "<br>");

  return html;
}
