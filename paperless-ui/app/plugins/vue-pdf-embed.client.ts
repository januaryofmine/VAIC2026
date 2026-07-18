import { GlobalWorkerOptions } from "pdfjs-dist";
// Vite serves the worker as a hashed asset (?url) so its version always matches
// the bundled pdfjs-dist — no stale copy in /public, no blob: worker (CSP-safe).
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import VuePdfEmbed from "vue-pdf-embed";
// Text layer = selectable text positioned over each page (needed for scroll-to-page
// anchors + highlights in Slice 15c; harmless now).
import "vue-pdf-embed/dist/styles/textLayer.css";

// Client-only plugin: vue-pdf-embed touches `window`/canvas at import, so it must
// never load during SSR. Registering it here keeps the viewer out of the server bundle.
export default defineNuxtPlugin((nuxtApp) => {
  GlobalWorkerOptions.workerSrc = workerUrl;
  nuxtApp.vueApp.component("VuePdfEmbed", VuePdfEmbed);
});
