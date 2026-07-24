import { useMutation } from "@tanstack/react-query";
import { outreachDraftService } from "../services/outreachDraftService";

export interface GenerateOutreachDraftInput {
  outreachType: string;
  executiveName?: string;
  talkingPoints: string[];
  opportunityId?: string;
  meetingBriefId?: string;
  context?: string;
}

// Priority 1: returns a GenerationJob, not the finished draft - the
// caller polls it with useGenerationJob and invalidates the
// ["outreach-drafts", companyId] list once that job completes.
export function useGenerateOutreachDraft(companyId: string | undefined) {
  return useMutation({
    mutationFn: (input: GenerateOutreachDraftInput) =>
      outreachDraftService.generate({ companyId: companyId as string, ...input }),
  });
}
