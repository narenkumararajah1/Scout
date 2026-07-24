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
import type { Report } from "../types/report";

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
};
