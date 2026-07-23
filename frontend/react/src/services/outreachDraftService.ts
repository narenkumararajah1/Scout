// Outreach Draft domain operations (V3 Phase 7C; outreach workflow
// redesign adds update() and send()). Generation
// (backend/services/outreach_service.py) and delivery
// (backend/services/outreach_delivery_service.py) are deliberately
// separate backend calls - generating a draft never requires an
// executive or recipient, and sending one never regenerates content.
import { apiRequest, apiRequestData } from "../api/client";
import type { OutreachDraft } from "../types/outreachDraft";

interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

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

  // Step 1 (Generate Draft): only company_id and outreach_type are
  // required - executiveName is optional so generation never blocks on
  // contact information. meetingBriefId lets the caller optionally tie
  // the draft to an already-generated Meeting Brief's summary, pulled
  // in server-side (no content duplicated here).
  async generate(input: {
    companyId: string;
    outreachType: string;
    executiveName?: string;
    talkingPoints: string[];
    opportunityId?: string;
    meetingBriefId?: string;
    context?: string;
  }): Promise<OutreachDraft> {
    return apiRequestData<OutreachDraft>("/api/v1/outreach-drafts", {
      method: "POST",
      body: {
        company_id: input.companyId,
        outreach_type: input.outreachType,
        executive_name: input.executiveName || undefined,
        talking_points: input.talkingPoints,
        opportunity_id: input.opportunityId || undefined,
        meeting_brief_id: input.meetingBriefId || undefined,
        context: input.context || undefined,
      },
    });
  },

  // Step 2 (Review): edit and save a draft's subject/content. Never
  // touches status.
  async update(draftId: string, input: { subject?: string; content: string }): Promise<OutreachDraft> {
    return apiRequestData<OutreachDraft>(`/api/v1/outreach-drafts/${draftId}`, {
      method: "PATCH",
      body: { subject: input.subject || undefined, content: input.content },
    });
  },

  // Step 3 (Delivery, "Send Through Scout"): the only call in this
  // service that can actually send a real message. Returns the
  // server's message too, since "delivered" vs "channel not
  // configured" are both 200s that read differently as a toast.
  async send(
    draftId: string,
    input: { channel: string; recipientEmail?: string; executiveName?: string },
  ): Promise<{ message: string; draft: OutreachDraft }> {
    const envelope = await apiRequest<Envelope<OutreachDraft>>(`/api/v1/outreach-drafts/${draftId}/send`, {
      method: "POST",
      body: {
        channel: input.channel,
        recipient_email: input.recipientEmail || undefined,
        executive_name: input.executiveName || undefined,
      },
    });
    return { message: envelope.message, draft: envelope.data };
  },
};
