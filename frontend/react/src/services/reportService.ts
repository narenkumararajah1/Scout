// Report domain operations (V3 Phase 7B read path; V2->V3 parity pass
// adds distributeReport()). Wraps V2's existing, unversioned report
// endpoints (backend/routers/reports.py, Phase 9) - no new backend
// work. distributeReport() sends this report to every eligible
// recipient across their preferred channels (a real send, via V2's
// existing POST /reports/{id}/distribute) - the UI requires an
// explicit confirmation before calling it, since it's the one action
// in this service with a genuine, irreversible side effect.
import { apiRequest } from "../api/client";
import type { Delivery } from "../types/delivery";
import type { Report } from "../types/report";

export const reportService = {
  async listCompanyReports(companyId: string): Promise<Report[]> {
    return apiRequest<Report[]>(`/companies/${companyId}/reports`);
  },

  async getReport(reportId: string): Promise<Report> {
    return apiRequest<Report>(`/reports/${reportId}`);
  },

  async getReportDeliveries(reportId: string): Promise<Delivery[]> {
    return apiRequest<Delivery[]>(`/reports/${reportId}/deliveries`);
  },

  async distributeReport(reportId: string): Promise<Delivery[]> {
    return apiRequest<Delivery[]>(`/reports/${reportId}/distribute`, { method: "POST" });
  },
};
