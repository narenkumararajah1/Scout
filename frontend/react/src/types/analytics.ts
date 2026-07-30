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

// Named distinctly from IntelligenceTimeline.tsx's own TimelineEvent,
// which is that component's prop shape and has since diverged (it carries
// a `detail` line and a "refresh" type). Two differently-shaped types
// sharing one name is a trap for the next reader.
//
// No longer rendered anywhere: V3 Enhancements Phase 2B repointed the
// company page's timeline at the Refresh Engine's snapshots, which carry
// per-run change counts. Kept because analytics_service.company_trends()
// still returns the field and this type should describe the payload
// honestly - see TECH_DEBT.md for the open question of whether the
// backend should stop computing it.
export interface CompanyTrendsTimelineEvent {
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
  timeline: CompanyTrendsTimelineEvent[];
}
