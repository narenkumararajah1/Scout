// Sales Playbook domain operations (V3 Phase 7C read/list/detail;
// V2->V3 parity pass adds generate(); Priority 1 makes generate()
// return a GenerationJob instead of blocking on the finished
// playbook - see useGenerationJob for how the caller picks up the
// result), wrapping the POST /api/v1/sales-playbooks endpoint.
import { apiRequestData } from "../api/client";
import type { GenerationJob } from "../types/generationJob";
import type { SalesPlaybook } from "../types/salesPlaybook";

export const salesPlaybookService = {
  async listForCompany(companyId: string): Promise<SalesPlaybook[]> {
    return apiRequestData<SalesPlaybook[]>(`/api/v1/sales-playbooks?company_id=${companyId}`);
  },

  async get(playbookId: string): Promise<SalesPlaybook> {
    return apiRequestData<SalesPlaybook>(`/api/v1/sales-playbooks/${playbookId}`);
  },

  async generate(companyId: string, opportunityId: string): Promise<GenerationJob> {
    return apiRequestData<GenerationJob>("/api/v1/sales-playbooks", {
      method: "POST",
      body: { company_id: companyId, opportunity_id: opportunityId },
    });
  },
};
