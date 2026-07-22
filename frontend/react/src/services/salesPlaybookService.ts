// Sales Playbook domain operations (V3 Phase 7C). Wraps the new
// read-only GET /api/v1/sales-playbooks endpoints - no generation
// trigger exists here, matching the backend's read-only scope.
import { apiRequestData } from "../api/client";
import type { SalesPlaybook } from "../types/salesPlaybook";

export const salesPlaybookService = {
  async listForCompany(companyId: string): Promise<SalesPlaybook[]> {
    return apiRequestData<SalesPlaybook[]>(`/api/v1/sales-playbooks?company_id=${companyId}`);
  },

  async get(playbookId: string): Promise<SalesPlaybook> {
    return apiRequestData<SalesPlaybook>(`/api/v1/sales-playbooks/${playbookId}`);
  },
};
