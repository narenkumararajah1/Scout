// Sales Playbook domain operations (V3 Phase 7C read/list/detail;
// V2->V3 parity pass adds generate(), wrapping the new
// POST /api/v1/sales-playbooks endpoint.
import { apiRequestData } from "../api/client";
import type { SalesPlaybook } from "../types/salesPlaybook";

export const salesPlaybookService = {
  async listForCompany(companyId: string): Promise<SalesPlaybook[]> {
    return apiRequestData<SalesPlaybook[]>(`/api/v1/sales-playbooks?company_id=${companyId}`);
  },

  async get(playbookId: string): Promise<SalesPlaybook> {
    return apiRequestData<SalesPlaybook>(`/api/v1/sales-playbooks/${playbookId}`);
  },

  async generate(companyId: string, opportunityId: string): Promise<SalesPlaybook> {
    return apiRequestData<SalesPlaybook>("/api/v1/sales-playbooks", {
      method: "POST",
      body: { company_id: companyId, opportunity_id: opportunityId },
    });
  },
};
