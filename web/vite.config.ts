import { existsSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const root = dirname(fileURLToPath(import.meta.url));
const skippedDirs = new Set(["node_modules", "dist", "public", "src", "scripts"]);

function pageEntries(): Record<string, string> {
  const entries: Record<string, string> = {};
  const landing = resolve(root, "index.html");
  if (existsSync(landing)) entries.index = landing;
  for (const dir of readdirSync(root, { withFileTypes: true })) {
    if (!dir.isDirectory() || skippedDirs.has(dir.name)) continue;
    for (const file of readdirSync(resolve(root, dir.name))) {
      if (!file.endsWith(".html")) continue;
      const name = file === "index.html" ? dir.name : `${dir.name}/${file.replace(/\.html$/, "")}`;
      entries[name] = resolve(root, dir.name, file);
    }
  }
  return entries;
}

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    rollupOptions: {
      input: { ...pageEntries(), sw: resolve(root, "src/sw.ts") },
      output: {
        entryFileNames: (chunk) => (chunk.name === "sw" ? "sw.js" : "assets/[name]-[hash].js"),
      },
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
