import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Porta fixa em 1420: é exatamente a origem que liberamos no CORS do
// backend (ver ALLOWED_ORIGINS em backend/app/main.py).
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    target: process.env.TAURI_ENV_PLATFORM === "windows" ? "chrome105" : "safari13",
    // Vite 8 passou a tratar esbuild como opcional (motor padrão agora é
    // baseado em oxc/rolldown); usei o minificador padrão em vez de
    // forçar "esbuild", que exigiria uma dependência extra só para isso.
    minify: !process.env.TAURI_ENV_DEBUG,
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    globals: true,
  },
});
