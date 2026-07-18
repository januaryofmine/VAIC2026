import { signUploadToken } from "../utils/upload-token";

/**
 * Issue a short-lived direct-upload ticket. The browser then POSTs the file straight
 * to retrieval-api `/api/ingest` with this HMAC token — bypassing Vercel's 4.5MB
 * function-body limit (large legal PDFs) while keeping the API key server-side only.
 */
export default defineEventHandler(async (event) => {
  const { user } = await requireUserSession(event);
  if (!user.id) throw createError({ statusCode: 401, statusMessage: "session expired" });

  const config = useRuntimeConfig();
  return {
    url: `${config.retrievalApiHost}/api/ingest`,
    token: signUploadToken(user.id, config.retrievalApiKey),
  };
});
