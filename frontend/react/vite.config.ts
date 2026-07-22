import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scout V3 React frontend. Proxies /api/v1 (V3's JWT-backed routes) and
// every unversioned V2 route this app's service layer actually calls
// (/companies, /reports, /analytics, /system, /recipients, /schedules,
// /workflow, /conversation - reused as-is, per "reuse existing backend
// endpoints" guidance across Phases 7A-7C and the V2->V3 parity pass) to
// the FastAPI backend during local development, so the SPA can call
// relative paths regardless of port.
//
// /companies, /reports, and /analytics are ALSO client-side route
// prefixes (CompaniesPage, ReportDetailPage, AnalyticsPage) - discovered
// during real browser verification that a direct navigation or page
// refresh on e.g. /companies returned the backend's raw JSON instead of
// the SPA. Vite's proxy has no CRA-style `bypass` option (that's
// http-proxy-middleware's API, not Vite's - a first attempt at this fix
// used it and silently did nothing); the actual fix is a small plugin
// middleware, registered before Vite installs its own proxy middleware,
// that rewrites the request to `/` whenever it looks like a real
// top-level browser navigation (`Accept: text/html`) rather than the
// app's own fetch() calls (which never send that header) - only then
// does react-router get a chance to handle the path instead of the
// backend.
function spaRoutesBeforeProxy(prefixes: string[]): Plugin {
  return {
    name: "spa-routes-before-proxy",
    configureServer(server) {
      function handleSpaRoute(req: IncomingMessage, res: ServerResponse, next: () => void): void {
        const url = req.url ?? "";
        const isNavigation = req.headers.accept?.includes("text/html") ?? false;
        const matchesSpaRoute = prefixes.some(
          (prefix) => url === prefix || url.startsWith(`${prefix}/`) || url.startsWith(`${prefix}?`),
        );
        if (isNavigation && matchesSpaRoute) {
          req.url = "/";
        }
        next();
      }
      server.middlewares.use(handleSpaRoute);
    },
  };
}

export default defineConfig({
  plugins: [spaRoutesBeforeProxy(["/companies", "/reports", "/analytics"]), react()],
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
      "/recipients": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/schedules": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/workflow": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/conversation": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
