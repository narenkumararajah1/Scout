import { useMutation } from "@tanstack/react-query";
import { meetingBriefService } from "../services/meetingBriefService";

// Priority 1: returns a GenerationJob, not the finished brief - the
// caller polls it with useGenerationJob and invalidates the
// ["meeting-briefs", companyId] list once that job completes.
export function useGenerateMeetingBrief(companyId: string | undefined) {
  return useMutation({
    mutationFn: (meetingTitle?: string) => meetingBriefService.generate(companyId as string, meetingTitle),
  });
}
