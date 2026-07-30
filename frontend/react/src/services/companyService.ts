// Company domain operations (V3 Phase 7A/7B). Wraps V2's unversioned
// /companies/* endpoints (backend/routers/companies.py, Phase 3/9) and
// this phase's new GET /api/v1/companies/{id}/intelligence
// (backend/api/routers/companies.py) - the frontend's only V3 addition
// for companies. analyzeCompany() (Phase 7B) wraps the existing,
// already-live POST /companies/{id}/analyze - no change to the
// analysis pipeline itself.
import { apiRequest, apiRequestData } from "../api/client";
import type { Company, CreateCompanyInput } from "../types/company";
import type { CompanyIntelligence } from "../types/companyIntelligence";
import type { CompanyRelationship, CreateCompanyRelationshipInput } from "../types/companyRelationship";
import type { CompanyVisitChanges } from "../types/companyView";
import type { ExecutiveOverview } from "../types/executive";
import type { RecentCompany } from "../types/recentCompany";
import type { CompanyVisualTrends } from "../types/visualTrends";
import type { CompanySnapshot, RefreshSummary } from "../types/refreshSummary";
import type { Report } from "../types/report";
import type { SalesCoachRecommendation } from "../types/salesCoach";

export const companyService = {
  async listCompanies(includeArchived = false): Promise<Company[]> {
    return apiRequest<Company[]>(`/companies${includeArchived ? "?include_archived=true" : ""}`);
  },

  async getCompany(companyId: string): Promise<Company> {
    return apiRequest<Company>(`/companies/${companyId}`);
  },

  async createCompany(input: CreateCompanyInput): Promise<Company> {
    return apiRequest<Company>("/companies", { method: "POST", body: input });
  },

  async enableMonitoring(companyId: string): Promise<Company> {
    return apiRequest<Company>(`/companies/${companyId}/enable`, { method: "POST" });
  },

  async disableMonitoring(companyId: string): Promise<Company> {
    return apiRequest<Company>(`/companies/${companyId}/disable`, { method: "POST" });
  },

  async getCompanyIntelligence(companyId: string): Promise<CompanyIntelligence> {
    return apiRequestData<CompanyIntelligence>(`/api/v1/companies/${companyId}/intelligence`);
  },

  // Roadmap Phase 3 - "What Changed Since Last Visit". Not idempotent:
  // each call both reads and advances the "last viewed" checkpoint, so
  // this should be called once per page open, not on every render.
  async visitCompany(companyId: string): Promise<CompanyVisitChanges> {
    return apiRequestData<CompanyVisitChanges>(`/api/v1/companies/${companyId}/visit`, { method: "POST" });
  },

  // Roadmap Phase 4, item 10 ("AI Sales Coach") - a real LLM call, so
  // it's opt-in from the UI (a button), not fetched automatically.
  async getSalesCoachRecommendation(companyId: string): Promise<SalesCoachRecommendation> {
    return apiRequestData<SalesCoachRecommendation>(`/api/v1/companies/${companyId}/sales-coach`);
  },

  // V3 Enhancements Phase 2 - the Company Refresh Engine. Read-only and
  // cheap: returns the summary already computed and stored by the last
  // analysis run, so opening a company page costs no LLM call. null when
  // the company has never been analysed, which is a normal state to
  // render rather than an error.
  async getRefreshSummary(companyId: string): Promise<RefreshSummary | null> {
    return apiRequestData<RefreshSummary | null>(`/api/v1/companies/${companyId}/refresh-summary`);
  },

  // One request returns the flat list, the org map and the ranked paths,
  // because they are three orderings of the same executives - fetching
  // them separately would let two views of one person disagree (V3
  // Enhancements Phase 4B).
  async getExecutives(companyId: string): Promise<ExecutiveOverview> {
    return apiRequestData<ExecutiveOverview>(`/api/v1/companies/${companyId}/executives`);
  },

  // The company's intelligence history shaped for charts. One request
  // feeds every visualisation on the page, so two charts can never
  // disagree about the same analysis run (V3 Enhancements Phase 5).
  async getVisualTrends(companyId: string): Promise<CompanyVisualTrends> {
    return apiRequestData<CompanyVisualTrends>(`/api/v1/companies/${companyId}/visual-trends`);
  },

  // V3 Enhancements Phase 6 - the quick company switcher. Reads the
  // visit rows visitCompany() above has been writing all along.
  async listRecentCompanies(limit = 6): Promise<RecentCompany[]> {
    return apiRequestData<RecentCompany[]>(`/api/v1/companies/recent/viewed?limit=${limit}`);
  },

  async listSnapshots(companyId: string, limit = 20): Promise<CompanySnapshot[]> {
    return apiRequestData<CompanySnapshot[]>(`/api/v1/companies/${companyId}/snapshots?limit=${limit}`);
  },

  async analyzeCompany(companyId: string): Promise<Report> {
    return apiRequest<Report>(`/companies/${companyId}/analyze`, { method: "POST" });
  },

  async archiveCompany(companyId: string): Promise<Company> {
    return apiRequest<Company>(`/companies/${companyId}/archive`, { method: "POST" });
  },

  async restoreCompany(companyId: string): Promise<Company> {
    return apiRequest<Company>(`/companies/${companyId}/restore`, { method: "POST" });
  },

  // Permanent deletion - a last resort, only allowed once a company has
  // already been archived (Priority 5).
  async removeCompany(companyId: string): Promise<void> {
    await apiRequest<void>(`/companies/${companyId}`, { method: "DELETE" });
  },

  // Roadmap Phase 6 - Relationship Intelligence (basic level). User-curated,
  // not AI-generated.
  async listRelationships(companyId: string): Promise<CompanyRelationship[]> {
    return apiRequestData<CompanyRelationship[]>(`/api/v1/companies/${companyId}/relationships`);
  },

  async addRelationship(companyId: string, input: CreateCompanyRelationshipInput): Promise<CompanyRelationship> {
    return apiRequestData<CompanyRelationship>(`/api/v1/companies/${companyId}/relationships`, {
      method: "POST",
      body: {
        relationship_type: input.relationshipType,
        related_company_id: input.relatedCompanyId || undefined,
        related_company_name: input.relatedCompanyName || undefined,
        notes: input.notes || undefined,
      },
    });
  },

  async removeRelationship(companyId: string, relationshipId: string): Promise<void> {
    await apiRequest<void>(`/api/v1/companies/${companyId}/relationships/${relationshipId}`, { method: "DELETE" });
  },
};
