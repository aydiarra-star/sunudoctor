import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// `base` is set so the built app works under GitHub Pages project URLs
// (https://<user>.github.io/<repo>/) as well as at a domain root.
export default defineConfig({
  base: process.env.VITE_BASE ?? "/",
  plugins: [react()],
  server: { port: 5173, host: true },
  build: { outDir: "dist", sourcemap: false },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
