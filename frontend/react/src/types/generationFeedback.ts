// AI feedback on a generated artifact (Priority 4). One shape covers
// every generation flow (Sales Playbook, Meeting Brief, Outreach
// Draft, Report) - see backend/schemas/generation_feedback.py.
export type FeedbackRating = "helpful" | "not_helpful" | "needs_improvement";

export interface GenerationFeedback {
  id: string;
  target_type: string;
  target_id: string;
  company_id: string | null;
  rating: FeedbackRating;
  note: string | null;
  created_at: string;
}

export interface SubmitGenerationFeedbackRequest {
  target_type: string;
  target_id: string;
  company_id?: string;
  rating: FeedbackRating;
  note?: string;
}
