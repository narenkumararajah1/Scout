// Feedback control for AI-generated content (Priority 4). One
// component covers every artifact type (Sales Playbook, Meeting
// Brief, Outreach Draft, Report) - target_type/target_id identify
// what was rated, mirroring GenerationJob's job_type/company_id reuse
// pattern from Priority 1. Persist-only: no retraining, no scoring,
// just a durable record for later human review.
import { useState } from "react";
import { useSubmitFeedback } from "../../hooks/useSubmitFeedback";
import type { FeedbackRating } from "../../types/generationFeedback";
import { getErrorMessage } from "../../utils/errors";

interface AIFeedbackProps {
  targetType: string;
  targetId: string;
  companyId?: string;
}

const RATING_OPTIONS: { rating: FeedbackRating; label: string }[] = [
  { rating: "helpful", label: "👍 Helpful" },
  { rating: "not_helpful", label: "👎 Not Helpful" },
  { rating: "needs_improvement", label: "Needs Improvement" },
];

export function AIFeedback({ targetType, targetId, companyId }: AIFeedbackProps) {
  const submitFeedback = useSubmitFeedback();
  const [selected, setSelected] = useState<FeedbackRating | null>(null);
  const [isNoteOpen, setIsNoteOpen] = useState(false);
  const [note, setNote] = useState("");

  function submit(rating: FeedbackRating, noteValue?: string) {
    submitFeedback.mutate(
      { target_type: targetType, target_id: targetId, company_id: companyId, rating, note: noteValue },
      {
        onSuccess: () => {
          setSelected(rating);
          setIsNoteOpen(false);
        },
      },
    );
  }

  function handleClick(rating: FeedbackRating) {
    if (rating === "needs_improvement") {
      setIsNoteOpen(true);
      return;
    }
    submit(rating);
  }

  if (selected) {
    return <div className="ai-feedback ai-feedback-thanks">Thanks for the feedback.</div>;
  }

  return (
    <div className="ai-feedback">
      <span className="ai-feedback-label">Was this helpful?</span>
      <div className="ai-feedback-buttons">
        {RATING_OPTIONS.map((option) => (
          <button
            key={option.rating}
            type="button"
            className="ai-feedback-button"
            onClick={() => handleClick(option.rating)}
            disabled={submitFeedback.isPending}
          >
            {option.label}
          </button>
        ))}
      </div>

      {isNoteOpen && (
        <div className="ai-feedback-note">
          <textarea
            placeholder="What should be improved? (optional)"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={2}
          />
          <div className="ai-feedback-note-actions">
            <button
              type="button"
              onClick={() => submit("needs_improvement", note || undefined)}
              disabled={submitFeedback.isPending}
            >
              {submitFeedback.isPending ? "Submitting..." : "Submit"}
            </button>
            <button type="button" onClick={() => setIsNoteOpen(false)} disabled={submitFeedback.isPending}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {submitFeedback.isError && <p className="ai-feedback-error">{getErrorMessage(submitFeedback.error)}</p>}
    </div>
  );
}
