// Mirrors backend/schemas/sales_playbook.py's SalesPlaybookOut exactly -
// a structured artifact, never flattened into free-form text.

export interface ObjectionHandlingItem {
  objection: string;
  response: string;
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
}
