// Mirrors backend/schemas/sales_playbook.py's SalesPlaybookOut exactly -
// a structured artifact, never flattened into free-form text.

export interface ObjectionHandlingItem {
  objection: string;
  response: string;
}

// Roadmap Phase 4, item 14 ("Explain Why Innominds?") - Customer Need
// -> Relevant Innominds Practices -> Relevant Experience -> Suggested
// Sales Motion, assembled server-side from already-persisted data.
export interface WhyInnominds {
  customer_need: string | null;
  relevant_practices: string[];
  relevant_experience: string[];
  suggested_sales_motion: string[];
}

export interface SalesPlaybook {
  id: string;
  company_id: string;
  opportunity_id: string | null;
  strategy_summary: string | null;
  discovery_questions: string[];
  talking_points: string[];
  objection_handling: ObjectionHandlingItem[];
  recommended_services: string[];
  next_steps: string[];
  risks: string[];
  confidence_score: number | null;
  created_at: string;
  why_innominds?: WhyInnominds;
}
