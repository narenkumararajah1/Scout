// Mirrors backend/schemas/meeting_brief.py's MeetingBriefOut exactly.

export interface ExecutiveProfile {
  name: string;
  title: string | null;
  biography: string | null;
}

export interface MeetingBrief {
  id: string;
  company_id: string;
  meeting_title: string | null;
  executive_summary: string | null;
  business_priorities: string[];
  executive_profiles: ExecutiveProfile[];
  talking_points: string[];
  discovery_questions: string[];
  recommended_services: string[];
  meeting_objectives: string[];
  confidence_score: number | null;
  created_at: string;
}
