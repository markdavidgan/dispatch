import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * Vite configuration for static demo builds.
 *
 * Swaps `@/lib/api` to the demo-mode wrapper that reads from baked-in JSON
 * files instead of calling a live backend.
 *
 * Usage: npm run build:demo
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: "@/lib/api", replacement: path.resolve(__dirname, "./src/lib/api.demo.ts") },
      { find: "@", replacement: path.resolve(__dirname, "./src") },
    ],
  },
  build: {
    outDir: "dist",
  },
});
