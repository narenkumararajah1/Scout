import { useMutation, useQueryClient } from "@tanstack/react-query";
import { outreachDraftService } from "../services/outreachDraftService";

// Wraps the two human-reviewer status actions (approve/archive) - both
// pure status transitions on an already-generated draft, never a send
// action. Invalidates both the list and the individual draft so either
// view (Outreach Drafts page or a detail view) picks up the new status.
export function useOutreachDraftActions(companyId: string | undefined) {
  const queryClient = useQueryClient();

  const invalidate = (draftId: string) => {
    void queryClient.invalidateQueries({ queryKey: ["outreach-drafts", companyId] });
    void queryClient.invalidateQueries({ queryKey: ["outreach-draft", draftId] });
  };

  const approve = useMutation({
    mutationFn: (draftId: string) => outreachDraftService.approve(draftId),
    onSuccess: (draft) => invalidate(draft.id),
  });

  const archive = useMutation({
    mutationFn: (draftId: string) => outreachDraftService.archive(draftId),
    onSuccess: (draft) => invalidate(draft.id),
  });

  return { approve, archive };
}
