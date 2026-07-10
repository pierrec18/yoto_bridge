import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Le backend FastAPI tourne sur :8000. En dev, on proxifie l'API et le
// streaming pour éviter tout souci de CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/stream": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
