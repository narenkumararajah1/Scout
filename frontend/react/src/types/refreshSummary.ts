// Company Refresh Engine (V3 Enhancements Phase 2B -
// docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md). Mirrors
// backend/schemas/company_snapshot.py.

// Signal-derived categories reuse the existing Signal.type vocabulary;
// the rest come from what the diff compares.
export type ChangeCategory =
  | "leadership"
  | "hiring"
  | "technology"
  | "strategic"
  | "opportunity"
  | "capability"
  | "profile";

export type ChangeType = "appeared" | "resolved" | "strengthened" | "weakened" | "updated";

export type ChangeSignificance = "major" | "minor";

export interface DetectedChange {
  category: ChangeCategory;
  change_type: ChangeType;
  title: string;
  detail: string | null;
  significance: ChangeSignificance;
  // Names the snapshot content the change was derived from
  // ("signal:leadership", "opportunity", "company_profile"), so the UI can
  // show why Scout believes something changed rather than just asserting it.
  source: string | null;
  previous_value: string | null;
  current_value: string | null;
}

export interface RefreshSummary {
  company_id: string;
  snapshot_id: string;
  previous_snapshot_id: string | null;
  captured_at: string;
  // No baseline existed, so nothing could be compared. Distinct from
  // content_unchanged below, which means a comparison ran and found
  // nothing - the UI has to say different things for those two.
  is_first_refresh: boolean;
  content_unchanged: boolean;
  changes: DetectedChange[];
  major_change_count: number;
  unchanged: string[];
  narrative: string | null;
  recommended_actions: string[];
  signal_count: number;
  opportunity_count: number;
}

export interface CompanySnapshot {
  id: string;
  company_id: string;
  research_session_id: string | null;
  captured_at: string;
  signal_count: number;
  opportunity_count: number;
  change_count: number;
  summary_narrative: string | null;
  recommended_actions: string[] | null;
}
