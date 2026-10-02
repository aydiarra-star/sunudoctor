import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// `base` is set so the built app works under GitHub Pages project URLs
// (https://<user>.github.io/<repo>/) as well as at a domain root.
// `__HASH_ROUTER__` is true for the static GitHub Pages build: GitHub Pages
// cannot rewrite deep links to index.html, so hash routing keeps every screen
// reachable with HTTP 200.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  define: {
    __HASH_ROUTER__: JSON.stringify(process.env.VITE_ROUTER === "hash"),
  },
  server: { port: 5173, host: true },
  build: { outDir: "dist", sourcemap: false },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
