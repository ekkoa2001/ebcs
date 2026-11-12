import { cpSync, mkdirSync } from "node:fs"
import { resolve } from "node:path"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

const web = resolve(__dirname, "../web")
const output = resolve(__dirname, "dist")

export default defineConfig({
  plugins: [
    vue(),
    {
      name: "copy-current-pages",
      closeBundle() {
        mkdirSync(output, { recursive: true })
        cpSync(web, output, { recursive: true })
      },
    },
  ],
  build: {
    outDir: resolve(__dirname, "empty"),
    emptyOutDir: true,
  },
})
