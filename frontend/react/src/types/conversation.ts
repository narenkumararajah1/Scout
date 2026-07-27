// Ask Scout / Scout Copilot (roadmap Phase 2: Core AI Experience).
// Mirrors backend/routers/conversation.py's request/response shapes.
export interface ConversationTurn {
  question: string;
  answer: string;
}

export interface RelatedCompany {
  id: string;
  name: string;
}

export type SuggestedActionType = "meeting_brief" | "outreach_draft" | "report";

export interface SuggestedAction {
  label: string;
  action_type: SuggestedActionType;
  company_id: string;
}

export interface AskScoutResult {
  answer: string;
  related_companies: RelatedCompany[];
  suggested_actions: SuggestedAction[];
}
