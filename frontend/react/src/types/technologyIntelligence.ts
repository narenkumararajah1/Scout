// Technology Intelligence (mirrors backend/schemas/technology_intelligence.py).
//
// The lifecycle *label and description* come from the backend rather than
// being mapped here. That is deliberate: the wording carries a claim
// Scout must not overstate - particularly that "not observed recently" is
// not evidence a company stopped using something - and a frontend that
// invented its own phrasing could quietly lose that care.

export type TechnologyLifecycle = "newly_detected" | "emerging" | "established" | "stale";

export interface TechnologyObservation {
  source: string;
  observed_at: string;
  research_session_id: string | null;
}

export interface TechnologyIntelligence {
  id: string;
  company_id: string;
  name: string;
  category: string | null;

  lifecycle: TechnologyLifecycle;
  lifecycle_label: string;
  lifecycle_description: string;

  first_seen_at: string | null;
  last_seen_at: string | null;
  observation_count: number;
  missed_count: number;
  consecutive_misses: number;
  // The observation rate, not a tuned score: observations / times looked.
  confidence: number;
  evidence_summary: string;
  observation_sources: TechnologyObservation[];
}
