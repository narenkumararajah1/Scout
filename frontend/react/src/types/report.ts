// Mirrors backend/models/report.py's V2 Report (backend/routers/reports.py).
// Distinct from the V3 Report (backend/database/models/report.py,
// `v3_reports` table) - that one has no JSON read endpoint yet, only
// PDF export (GET /api/v1/reports/{id}/export?format=pdf); viewing it
// is deferred to a later phase.

export interface Report {
  id: string;
  company_id: string;
  research_session_id: string;
  executive_summary: string | null;
  company_overview: string | null;
  key_findings: string | null;
  technology_analysis: string | null;
  capability_alignment: string | null;
  opportunities_section: string | null;
  recommendations: string | null;
  talking_points: string | null;
  created_at: string;
}
