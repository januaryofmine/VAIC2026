// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: false },
  // Fixed port so the GitHub OAuth callback (…:3100/api/auth/github) always matches.
  devServer: { port: 3100 },
  modules: ["@nuxt/ui", "@nuxt/fonts", "nuxt-auth-utils"],
  // The design is light-only; don't follow OS dark mode. A fresh storageKey ignores
  // any stale 'dark' a browser stored before this was set (else it would override).
  colorMode: { preference: "light", fallback: "light", storageKey: "pl-color-mode" },
  css: ["~/assets/css/main.css"],
  app: {
    head: { title: "Paperless Meetings" },
  },
  // Pre-bundle the PDF viewer so Vite resolves its worker asset cleanly in dev.
  vite: {
    optimizeDeps: { include: ["vue-pdf-embed"] },
  },
  runtimeConfig: {
    // NUXT_RETRIEVAL_API_HOST overrides in prod
    retrievalApiHost: "http://localhost:8001",
    // Shared secret for the retrieval-api (X-API-Key). NUXT_RETRIEVAL_API_KEY in prod.
    // Empty in local dev → retrieval-api leaves its endpoints open.
    retrievalApiKey: "",
    ai: {
      // Anthropic key is read from ANTHROPIC_API_KEY by the AI SDK directly.
      // provider: "anthropic" (default) | "openai-compatible" (e.g. 9router gateway).
      // Override with NUXT_AI_PROVIDER / NUXT_AI_BASE_URL / NUXT_AI_API_KEY, and set the
      // model names below to whatever the gateway exposes (e.g. oc/deepseek-v4-flash-free).
      provider: "anthropic",
      baseUrl: "http://localhost:20128/v1",
      apiKey: "",
      // Reasoning models return EMPTY content unless thinking is disabled — see provider.ts.
      disableReasoning: true,
      summarizeMapModel: "claude-haiku-4-5-20251001", // cheap/fast for the map step
      summarizeReduceModel: "claude-sonnet-4-6", // quality for structured reduce
      chatModel: "claude-sonnet-4-6",
      planModel: "claude-haiku-4-5-20251001", // cheap/fast: plan the Q&A search strategy
      temperature: 0.3,
      askTopK: 6, // chunks retrieved per sub-query in the fan-out
      askMaxChunks: 12, // cap on the merged chunk set fed to synthesis
      // map-reduce tuning for the <60s budget: fewer, larger groups + capped concurrency.
      // Concurrency 10 is safe (no per-call throttling observed); bigger groups = fewer waves.
      mapGroupChars: 30000,
      mapConcurrency: 10,
    },
    ingest: {
      // resolved relative to the server cwd (paperless-ui). NUXT_INGEST_RAG_PIPELINE_DIR overrides.
      ragPipelineDir: "../rag-pipeline",
      maxFileMb: 25,
    },
  },
});
