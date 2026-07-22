// V3 Report domain operations (V3 Phase 7C). Wraps the new read-only
// GET /api/v1/reports list/detail endpoints, plus Phase 6's PDF export
// route (a raw file download, so it navigates the browser directly
// rather than going through apiRequest's JSON parsing). No generation
// trigger exists here - viewing/exporting only.
import { apiRequestData, getStoredToken } from "../api/client";
import type { V3Report } from "../types/v3Report";

export const v3ReportService = {
  async listForCompany(companyId: string): Promise<V3Report[]> {
    return apiRequestData<V3Report[]>(`/api/v1/reports?company_id=${companyId}`);
  },

  async get(reportId: string): Promise<V3Report> {
    return apiRequestData<V3Report>(`/api/v1/reports/${reportId}`);
  },

  async downloadPdf(reportId: string): Promise<void> {
    const token = getStoredToken();
    const response = await fetch(`/api/v1/reports/${reportId}/export?format=pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) {
      throw new Error(`Failed to export report ${reportId} as PDF.`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `report-${reportId}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  },
};
