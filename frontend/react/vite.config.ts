import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scout V3 React frontend. Proxies /api/v1 to the FastAPI backend during
// local development so the SPA can call relative paths regardless of port.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
