import { useMutation, useQueryClient } from "@tanstack/react-query";
import { outreachDraftService } from "../services/outreachDraftService";

export interface GenerateOutreachDraftInput {
  outreachType: string;
  executiveName: string;
  talkingPoints: string[];
  opportunityId?: string;
  context?: string;
}

export function useGenerateOutreachDraft(companyId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: GenerateOutreachDraftInput) =>
      outreachDraftService.generate({ companyId: companyId as string, ...input }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["outreach-drafts", companyId] });
    },
  });
}
