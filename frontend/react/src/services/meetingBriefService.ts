// Meeting Brief domain operations (V3 Phase 7C). Wraps the new
// read-only GET /api/v1/meeting-briefs endpoints - no generation
// trigger exists here, matching the backend's read-only scope.
import { apiRequestData } from "../api/client";
import type { MeetingBrief } from "../types/meetingBrief";

export const meetingBriefService = {
  async listForCompany(companyId: string): Promise<MeetingBrief[]> {
    return apiRequestData<MeetingBrief[]>(`/api/v1/meeting-briefs?company_id=${companyId}`);
  },

  async get(briefId: string): Promise<MeetingBrief> {
    return apiRequestData<MeetingBrief>(`/api/v1/meeting-briefs/${briefId}`);
  },
};
