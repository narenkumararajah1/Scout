// Mirrors backend/models/opportunity.py.

export interface Opportunity {
  id: string;
  company_id: string;
  research_session_id: string;
  title: string;
  description: string | null;
  priority: number | null;
  confidence_score: number | null;
  supporting_signal_ids: string[];
  capability_match_ids: string[];
  recommended_services: string[];
  recommended_case_studies: string[];
  generated_date: string;
}
