import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scout V3 React frontend. Proxies /api/v1 (V3's JWT-backed routes) and
// every unversioned V2 route this app's service layer actually calls
// (/companies, /reports, /analytics, /system - reused as-is, per
// "reuse existing backend endpoints" guidance across Phases 7A-7C) to
// the FastAPI backend during local development, so the SPA can call
// relative paths regardless of port.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/companies": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/reports": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/analytics": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/system": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
