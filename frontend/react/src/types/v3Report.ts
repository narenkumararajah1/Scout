// Mirrors backend/schemas/v3_report.py's V3ReportOut exactly - distinct
// from types/report.ts, which is the V2 Report. `content`'s shape
// matches backend/services/v3_report_service.py's _serialize_*()
// helpers field-for-field - rendered as-is, never regenerated on view.

export interface CompanyIntelligenceSummary {
  name: string;
  industry: string | null;
  headquarters: string | null;
  business_initiatives: string[];
}

export interface TechnologyLandscapeItem {
  name: string;
  category: string | null;
  adoption_status: string | null;
  business_relevance: string | null;
}

export interface OpportunityAnalysisItem {
  title: string;
  description: string | null;
  priority: number | null;
  confidence_score: number | null;
  recommended_services: string[];
}

export interface CapabilityAlignmentItem {
  capability_name: string;
  confidence: number;
  reasoning: string;
}

export interface ExecutiveIntelligenceItem {
  name: string;
  title: string | null;
  biography: string | null;
  business_priorities: string[] | null;
}

export interface SalesPlaybookSummary {
  strategy_summary: string | null;
  talking_points: string[];
  recommended_services: string[];
  next_steps: string[];
  risks: string[];
}

export interface MeetingBriefSummary {
  meeting_title: string | null;
  meeting_objectives: string[];
  talking_points: string[];
}

export interface OutreachDraftSummary {
  type: string;
  subject: string | null;
  status: string;
}

export interface V3ReportContent {
  company_intelligence?: CompanyIntelligenceSummary;
  technology_landscape?: TechnologyLandscapeItem[];
  opportunity_analysis?: OpportunityAnalysisItem[];
  capability_alignment?: CapabilityAlignmentItem[];
  executive_intelligence?: ExecutiveIntelligenceItem[];
  sales_playbooks?: SalesPlaybookSummary[];
  meeting_briefs?: MeetingBriefSummary[];
  outreach_drafts?: OutreachDraftSummary[];
}

export interface V3Report {
  id: string;
  company_id: string;
  report_type: string;
  title: string | null;
  executive_summary: string | null;
  version: number;
  status: string;
  content: V3ReportContent | null;
  created_at: string;
}
