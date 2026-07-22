// Analytics domain operations (V3 Phase 7B). Wraps V2's existing,
// unversioned analytics endpoints (backend/routers/analytics.py,
// Phase 9) exactly as they return data - no new aggregation happens
// here or in any component, per the approved Phase 7B plan.
import { apiRequest } from "../api/client";
import type { CompanyTrends } from "../types/analytics";
import type { Opportunity } from "../types/opportunity";

export const analyticsService = {
  async opportunityRankings(limit = 20): Promise<Opportunity[]> {
    return apiRequest<Opportunity[]>(`/analytics/opportunities?limit=${limit}`);
  },

  async companyTrends(companyId: string): Promise<CompanyTrends> {
    return apiRequest<CompanyTrends>(`/analytics/companies/${companyId}/trends`);
  },
};
