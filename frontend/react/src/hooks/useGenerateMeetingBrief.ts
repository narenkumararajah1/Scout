import { useMutation, useQueryClient } from "@tanstack/react-query";
import { meetingBriefService } from "../services/meetingBriefService";

export function useGenerateMeetingBrief(companyId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (meetingTitle?: string) => meetingBriefService.generate(companyId as string, meetingTitle),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["meeting-briefs", companyId] });
    },
  });
}
