// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: false },
  modules: ["@nuxt/ui"],
  css: ["~/assets/css/main.css"],
  app: {
    head: { title: "Paperless Meetings" },
  },
  runtimeConfig: {
    // NUXT_RETRIEVAL_API_HOST overrides in prod
    retrievalApiHost: "http://localhost:8001",
    ai: {
      // Anthropic key is read from ANTHROPIC_API_KEY by the AI SDK directly.
      summarizeMapModel: "claude-haiku-4-5-20251001", // cheap/fast for the map step
      summarizeReduceModel: "claude-sonnet-4-6", // quality for structured reduce
      chatModel: "claude-sonnet-4-6",
      temperature: 0.3,
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
