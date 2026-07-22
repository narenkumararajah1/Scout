// Outreach Draft domain operations (V3 Phase 7C). Wraps
// GET /api/v1/outreach-drafts (list/detail) and the two human-reviewer
// status actions (approve/archive) - never a send action; Scout has no
// delivery capability anywhere in this codebase.
import { apiRequestData } from "../api/client";
import type { OutreachDraft } from "../types/outreachDraft";

export const outreachDraftService = {
  async listForCompany(companyId: string): Promise<OutreachDraft[]> {
    return apiRequestData<OutreachDraft[]>(`/api/v1/outreach-drafts?company_id=${companyId}`);
  },

  async get(draftId: string): Promise<OutreachDraft> {
    return apiRequestData<OutreachDraft>(`/api/v1/outreach-drafts/${draftId}`);
  },

  async approve(draftId: string): Promise<OutreachDraft> {
    return apiRequestData<OutreachDraft>(`/api/v1/outreach-drafts/${draftId}/approve`, { method: "POST" });
  },

  async archive(draftId: string): Promise<OutreachDraft> {
    return apiRequestData<OutreachDraft>(`/api/v1/outreach-drafts/${draftId}/archive`, { method: "POST" });
  },

  async generate(input: {
    companyId: string;
    outreachType: string;
    executiveName: string;
    talkingPoints: string[];
    opportunityId?: string;
    context?: string;
  }): Promise<OutreachDraft> {
    return apiRequestData<OutreachDraft>("/api/v1/outreach-drafts", {
      method: "POST",
      body: {
        company_id: input.companyId,
        outreach_type: input.outreachType,
        executive_name: input.executiveName,
        talking_points: input.talkingPoints,
        opportunity_id: input.opportunityId || undefined,
        context: input.context || undefined,
      },
    });
  },
};
