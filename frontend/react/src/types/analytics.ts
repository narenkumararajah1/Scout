import type { Opportunity } from "./opportunity";
import type { Report } from "./report";

// Mirrors backend/services/analytics_service.py's company_trends() raw
// dict return shape exactly - no new aggregation happens on the
// frontend, per the approved Phase 7B scope.

export interface ResearchSessionSummary {
  id: string;
  company_id: string;
  execution_time: string;
  research_summary: string | null;
  status: string;
}

export interface OpportunityHistoryPoint {
  date: string;
  title: string;
  confidence_score: number | null;
  priority: number | null;
}

export interface TimelineEvent {
  date: string;
  type: "research" | "opportunity" | "report";
  label: string;
}

export interface CompanyTrends {
  company_id: string;
  company_name: string;
  research_session_count: number;
  opportunity_count: number;
  report_count: number;
  average_opportunity_confidence: number | null;
  top_opportunities: Opportunity[];
  research_sessions: ResearchSessionSummary[];
  reports: Report[];
  opportunity_history: OpportunityHistoryPoint[];
  timeline: TimelineEvent[];
}
