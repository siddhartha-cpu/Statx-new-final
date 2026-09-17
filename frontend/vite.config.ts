import path from "node:path";
import { defineConfig, type UserConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const hotReloadDisabled = process.env.DISABLE_HOT_RELOAD === "true";
if (!hotReloadDisabled) process.env.CHOKIDAR_USEPOLLING = "true";

export default defineConfig(() => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      { find: "@", replacement: path.resolve(__dirname, "./src") },
      { find: /^lucide-react$/, replacement: path.resolve(__dirname, "./src/lib/lucide-react.tsx") },
      { find: "lucide-react-upstream", replacement: path.resolve(__dirname, "./node_modules/lucide-react") },
      { find: /^recharts$/, replacement: path.resolve(__dirname, "./src/lib/recharts.tsx") },
      { find: "recharts-upstream", replacement: path.resolve(__dirname, "./node_modules/recharts") },
    ],
  },
  server: {
    host: true,
    port: 3000,
    allowedHosts: true,
    cors: true,
    hmr: hotReloadDisabled ? false : { overlay: true },
    watch: hotReloadDisabled ? null : { usePolling: true, interval: 300 },
    proxy: { "/api": { target: "http://localhost:8001", changeOrigin: true } },
  },
} satisfies UserConfig));