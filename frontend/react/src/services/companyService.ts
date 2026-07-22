// Company domain operations (V3 Phase 7A). Wraps V2's unversioned
// /companies/* endpoints (backend/routers/companies.py, Phase 3) and
// this phase's new GET /api/v1/companies/{id}/intelligence
// (backend/api/routers/companies.py) - the frontend's only V3 addition
// for companies.
import { apiRequest, apiRequestData } from "../api/client";
import type { Company, CreateCompanyInput } from "../types/company";
import type { CompanyIntelligence } from "../types/companyIntelligence";

export const companyService = {
  async listCompanies(): Promise<Company[]> {
    return apiRequest<Company[]>("/companies");
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
};
