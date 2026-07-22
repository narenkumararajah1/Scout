import { useQuery } from "@tanstack/react-query";
import { outreachDraftService } from "../services/outreachDraftService";

export function useOutreachDraft(draftId: string | undefined) {
  return useQuery({
    queryKey: ["outreach-draft", draftId],
    queryFn: () => outreachDraftService.get(draftId as string),
    enabled: draftId !== undefined,
  });
}
