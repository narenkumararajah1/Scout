// Displays an Outreach Draft (V3 Phase 6) with the two human-reviewer
// actions this page adds: Approve/Archive. Both are pure status
// transitions - this page has no send/deliver capability whatsoever,
// matching the backend's architectural invariant exactly.
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useOutreachDraft } from "../hooks/useOutreachDraft";
import { useOutreachDraftActions } from "../hooks/useOutreachDraftActions";
import { useToasts } from "../hooks/useToasts";
import { getErrorMessage } from "../utils/errors";

export function OutreachDraftDetailPage() {
  const { draftId } = useParams<{ draftId: string }>();
  const draftQuery = useOutreachDraft(draftId);
  const { approve, archive } = useOutreachDraftActions(draftQuery.data?.company_id);
  const { toasts, pushToast, dismissToast } = useToasts();

  if (!draftId) {
    return <ErrorState message="No outreach draft selected." />;
  }

  if (draftQuery.isLoading) {
    return <LoadingState message="Loading outreach draft..." />;
  }

  if (draftQuery.isError || !draftQuery.data) {
    return (
      <ErrorState message={draftQuery.error ? getErrorMessage(draftQuery.error) : "Outreach draft not found."} />
    );
  }

  const draft = draftQuery.data;
  const isPending = approve.isPending || archive.isPending;

  function handleApprove() {
    approve.mutate(draftId as string, {
      onSuccess: () => pushToast("Draft approved.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleArchive() {
    archive.mutate(draftId as string, {
      onSuccess: () => pushToast("Draft archived.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  return (
    <div className="outreach-draft-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className="page-header">
        <h1>{draft.type}</h1>
        <Badge
          label={draft.status}
          variant={draft.status === "Approved" ? "success" : draft.status === "Archived" ? "neutral" : "warning"}
        />
        {draft.status === "Draft" && (
          <>
            <button type="button" onClick={handleApprove} disabled={isPending}>
              Approve
            </button>
            <button type="button" onClick={handleArchive} disabled={isPending}>
              Archive
            </button>
          </>
        )}
      </div>

      <Card title="Subject">
        <p className="report-section-text">{draft.subject ?? "(no subject)"}</p>
      </Card>

      <Card title="Content">
        <p className="report-section-text">{draft.content}</p>
      </Card>
    </div>
  );
}
