// System status domain operations (V3 Phase 7C). Wraps V2's existing,
// unversioned GET /system/status (backend/routers/system.py, Phase 9) -
// no new backend work; Settings only ever presents read-only status,
// never fabricated preferences/integrations/API keys.
import { apiRequest } from "../api/client";
import type { SystemStatus } from "../types/systemStatus";

export const systemService = {
  async getStatus(): Promise<SystemStatus> {
    return apiRequest<SystemStatus>("/system/status", { auth: false });
  },
};
