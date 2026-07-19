import { flushTraces, isTracingEnabled } from "../utils/llm-trace";

/**
 * Gửi trace no-op an toàn, nhưng trên serverless (Vercel) function có thể bị đóng
 * băng NGAY khi response gửi xong → các POST trace fire-and-forget (traceLLM) bị rớt
 * âm thầm — đúng thứ khiến observability trở nên vô dụng ở môi trường deploy thật.
 *
 * `afterResponse` chạy sau mỗi request; đăng ký `flushTraces()` với `waitUntil` để
 * giữ function sống tới khi các POST hoàn tất. No-op khi tắt tracing; và vô hại trên
 * node server dài hạn (waitUntil = undefined ở đó, nhưng tiến trình sống nên POST vẫn
 * gửi xong bình thường).
 */
export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook("afterResponse", (event) => {
    if (!isTracingEnabled()) return;
    event.context.waitUntil?.(flushTraces());
  });
});
