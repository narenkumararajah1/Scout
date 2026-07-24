// Displays an Outreach Draft (V3 Phase 6). Outreach workflow redesign:
// generation (Step 1, Company Details) and delivery (Step 3, here) are
// deliberately separate - this page adds Review (Step 2: read, edit,
// copy, save) and "Send Through Scout" (Step 3: the only action on this
// page that can send a real message, gated behind a confirmation
// dialog exactly like Report Distribution already is).
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AIFeedback } from "../components/ui/AIFeedback";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useConfirm } from "../hooks/useConfirm";
import { useOutreachDraft } from "../hooks/useOutreachDraft";
import { useOutreachDraftActions } from "../hooks/useOutreachDraftActions";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useToasts } from "../hooks/useToasts";
import { getErrorMessage } from "../utils/errors";
import { outreachStatusVariant } from "../utils/outreachDraft";

const DELIVERY_CHANNELS = ["email", "teams"];

export function OutreachDraftDetailPage() {
  const { draftId } = useParams<{ draftId: string }>();
  const draftQuery = useOutreachDraft(draftId);
  const { approve, archive, update, send } = useOutreachDraftActions(draftQuery.data?.company_id);
  const { toasts, pushToast, dismissToast } = useToasts();
  const { confirm, confirmDialog } = useConfirm();
  const statusQuery = useSystemStatus();

  const [isEditing, setIsEditing] = useState(false);
  const [editSubject, setEditSubject] = useState("");
  const [editContent, setEditContent] = useState("");

  const [isSendFormOpen, setIsSendFormOpen] = useState(false);
  const [channel, setChannel] = useState(DELIVERY_CHANNELS[0]);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [sendExecutiveName, setSendExecutiveName] = useState("");

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
  const isReviewPending = approve.isPending || archive.isPending;

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

  function handleStartEdit() {
    setEditSubject(draft.subject ?? "");
    setEditContent(draft.content);
    setIsEditing(true);
  }

  function handleSave() {
    update.mutate(
      { draftId: draftId as string, subject: editSubject || undefined, content: editContent },
      {
        onSuccess: () => {
          pushToast("Draft saved.", "success");
          setIsEditing(false);
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  async function handleCopy() {
    const text = draft.subject ? `Subject: ${draft.subject}\n\n${draft.content}` : draft.content;
    await navigator.clipboard.writeText(text);
    pushToast("Copied to clipboard.", "success");
  }

  async function handleSend() {
    if (channel === "email" && !recipientEmail) {
      pushToast("Enter a recipient email first.", "error");
      return;
    }
    // Priority 6 (production safety): wording reflects whether this will
    // actually leave the building or just log what would have been sent.
    const delivery = statusQuery.data?.delivery;
    const isLive = delivery ? (channel === "email" ? delivery.email_live : delivery.teams_live) : true;
    const description = isLive
      ? channel === "email"
        ? `Send this draft to ${recipientEmail} by email now? This sends a real message and can't be undone.`
        : "Post this draft to the configured Teams channel now? This sends a real message and can't be undone."
      : `Send this draft ${channel === "email" ? `to ${recipientEmail} by email` : "to Teams"} now? Delivery is currently in dry-run mode - no real message will be sent.`;
    if (!(await confirm(description))) {
      return;
    }
    send.mutate(
      {
        draftId: draftId as string,
        channel,
        recipientEmail: channel === "email" ? recipientEmail : undefined,
        executiveName: sendExecutiveName || undefined,
      },
      {
        onSuccess: (result) => {
          pushToast(result.message, result.draft.status === "Sent" ? "success" : "info");
          setIsSendFormOpen(false);
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  return (
    <div className="outreach-draft-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <Link to={`/companies/${draft.company_id}`} className="breadcrumb-back">
        ← Back to company
      </Link>

      <div className="page-header">
        <h1>{draft.type}</h1>
        <Badge label={draft.status} variant={outreachStatusVariant(draft.status)} />
        {!isEditing && (
          <>
            <button type="button" onClick={handleCopy}>
              Copy
            </button>
            <button type="button" onClick={handleStartEdit}>
              Edit
            </button>
            {draft.status === "Draft" && (
              <>
                <button type="button" onClick={handleApprove} disabled={isReviewPending}>
                  Approve
                </button>
                <button type="button" onClick={handleArchive} disabled={isReviewPending}>
                  Archive
                </button>
              </>
            )}
            <button type="button" onClick={() => setIsSendFormOpen((open) => !open)}>
              {isSendFormOpen ? "Cancel send" : "Send Through Scout"}
            </button>
          </>
        )}
      </div>

      {isSendFormOpen && !isEditing && (
        <Card title="Send Through Scout">
          <p className="card-description">
            Generating a draft never requires this - only sending one does. Choose a channel and who it's going
            to; this is the one action on this page that sends a real message.
          </p>
          <div className="send-outreach-form">
            <label htmlFor="send-channel">Channel</label>
            <select id="send-channel" value={channel} onChange={(event) => setChannel(event.target.value)}>
              {DELIVERY_CHANNELS.map((option) => (
                <option key={option} value={option}>
                  {option === "email" ? "Email" : "Microsoft Teams"}
                </option>
              ))}
            </select>
            {channel === "email" && (
              <>
                <label htmlFor="send-recipient">Recipient email</label>
                <input
                  id="send-recipient"
                  type="email"
                  placeholder="executive@company.com"
                  value={recipientEmail}
                  onChange={(event) => setRecipientEmail(event.target.value)}
                  required
                />
              </>
            )}
            <label htmlFor="send-executive">Executive (optional)</label>
            <input
              id="send-executive"
              type="text"
              placeholder="Who this is for"
              value={sendExecutiveName}
              onChange={(event) => setSendExecutiveName(event.target.value)}
            />
            <button type="button" onClick={handleSend} disabled={send.isPending}>
              {send.isPending ? "Sending..." : "Send"}
            </button>
          </div>
        </Card>
      )}

      <Card title="Subject">
        {isEditing ? (
          <input
            type="text"
            className="outreach-edit-subject"
            value={editSubject}
            onChange={(event) => setEditSubject(event.target.value)}
            placeholder="(no subject)"
          />
        ) : (
          <p className="report-section-text">{draft.subject ?? "(no subject)"}</p>
        )}
      </Card>

      <Card title="Content">
        {isEditing ? (
          <>
            <textarea
              className="outreach-edit-content"
              value={editContent}
              onChange={(event) => setEditContent(event.target.value)}
              rows={12}
            />
            <div className="outreach-edit-actions">
              <button type="button" onClick={handleSave} disabled={update.isPending}>
                {update.isPending ? "Saving..." : "Save"}
              </button>
              <button type="button" onClick={() => setIsEditing(false)} disabled={update.isPending}>
                Cancel
              </button>
            </div>
          </>
        ) : (
          <p className="report-section-text">{draft.content}</p>
        )}
      </Card>

      <AIFeedback targetType="outreach_draft" targetId={draft.id} companyId={draft.company_id} />
    </div>
  );
}
