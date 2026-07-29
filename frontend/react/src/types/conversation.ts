// Ask Scout / Scout Copilot (roadmap Phase 2: Core AI Experience).
// Mirrors backend/routers/conversation.py's request/response shapes.
import type { KnowledgeReference } from "./knowledgeDocument";

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
  // The Innominds knowledge passages that grounded the answer (V3
  // Enhancements Phase 1). The bracketed [1]/[2] markers in `answer`
  // refer to these by position, so the order must be preserved when
  // rendering. Empty when nothing relevant was retrieved, which is the
  // normal state before any knowledge has been ingested.
  knowledge_sources: KnowledgeReference[];
}
