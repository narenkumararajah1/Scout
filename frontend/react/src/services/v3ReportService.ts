// Report domain operations (V3 Phase 7C). Wraps the read-only
// GET /api/v1/reports list/detail endpoints, plus Phase 6's PDF export
// route (a raw file download, so it navigates the browser directly
// rather than going through apiRequest's JSON parsing). generate()
// returns a GenerationJob rather than blocking on the finished report
// (Priority 1) - see useGenerationJob for how the caller picks up the
// result once it completes.
import { apiRequestData, getStoredToken } from "../api/client";
import type { GenerationJob } from "../types/generationJob";
import type { Delivery } from "../types/delivery";
import type { V3Report } from "../types/v3Report";

export const v3ReportService = {
  // Distribution goes through the same delivery service V2 reports use;
  // the backend adapts this report into the shape those senders read.
  // Returns one Delivery record per recipient/channel attempt, including
  // skipped and failed ones, so the UI can report the whole outcome.
  async distributeIntelligenceReport(reportId: string): Promise<Delivery[]> {
    return apiRequestData<Delivery[]>(`/api/v1/reports/${reportId}/distribute`, { method: "POST" });
  },

  async listForCompany(companyId: string): Promise<V3Report[]> {
    return apiRequestData<V3Report[]>(`/api/v1/reports?company_id=${companyId}`);
  },

  async get(reportId: string): Promise<V3Report> {
    return apiRequestData<V3Report>(`/api/v1/reports/${reportId}`);
  },

  async generate(companyId: string, title?: string): Promise<GenerationJob> {
    return apiRequestData<GenerationJob>("/api/v1/reports", {
      method: "POST",
      body: { company_id: companyId, title: title || undefined },
    });
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
