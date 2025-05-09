import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Built output goes straight into the Python package so `ka serve` can serve it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: "../src/knowledge_assistant/static", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
  test: { environment: "node" },
});
