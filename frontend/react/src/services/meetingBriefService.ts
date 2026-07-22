// Meeting Brief domain operations (V3 Phase 7C read/list/detail;
// V2->V3 parity pass adds generate(), wrapping the new
// POST /api/v1/meeting-briefs endpoint.
import { apiRequestData } from "../api/client";
import type { MeetingBrief } from "../types/meetingBrief";

export const meetingBriefService = {
  async listForCompany(companyId: string): Promise<MeetingBrief[]> {
    return apiRequestData<MeetingBrief[]>(`/api/v1/meeting-briefs?company_id=${companyId}`);
  },

  async get(briefId: string): Promise<MeetingBrief> {
    return apiRequestData<MeetingBrief>(`/api/v1/meeting-briefs/${briefId}`);
  },

  async generate(companyId: string, meetingTitle?: string): Promise<MeetingBrief> {
    return apiRequestData<MeetingBrief>("/api/v1/meeting-briefs", {
      method: "POST",
      body: { company_id: companyId, meeting_title: meetingTitle || undefined },
    });
  },
};
