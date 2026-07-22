// Report domain operations (V3 Phase 7B). Wraps V2's existing,
// unversioned report endpoints (backend/routers/reports.py, Phase 9) -
// no new backend work; this phase only adds a frontend read path over
// what already exists. Report distribution
// (POST /reports/{id}/distribute) is intentionally not wrapped here -
// it sends real email through V2's recipient system and is out of
// scope for this phase's frontend, per the approved Phase 7B plan.
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
};
