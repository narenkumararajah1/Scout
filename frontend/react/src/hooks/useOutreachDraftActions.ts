import { useMutation, useQueryClient } from "@tanstack/react-query";
import { outreachDraftService } from "../services/outreachDraftService";

// Wraps the human-reviewer status actions (approve/archive), plus the
// outreach workflow redesign's two new actions: update() for Step 2
// (Review - edit and save content) and send() for Step 3 (Delivery -
// "Send Through Scout", the only one of these that can actually send a
// real message). Invalidates both the list and the individual draft so
// either view (Outreach Drafts page or a detail view) picks up changes.
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

  const update = useMutation({
    mutationFn: ({ draftId, subject, content }: { draftId: string; subject?: string; content: string }) =>
      outreachDraftService.update(draftId, { subject, content }),
    onSuccess: (draft) => invalidate(draft.id),
  });

  const send = useMutation({
    mutationFn: ({
      draftId,
      channel,
      recipientEmail,
      executiveName,
    }: {
      draftId: string;
      channel: string;
      recipientEmail?: string;
      executiveName?: string;
    }) => outreachDraftService.send(draftId, { channel, recipientEmail, executiveName }),
    onSuccess: (result) => invalidate(result.draft.id),
  });

  return { approve, archive, update, send };
}
