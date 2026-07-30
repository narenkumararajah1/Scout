// Relationship Intelligence (V3 Enhancements Phase 4B -
// docs/v3-enhancements/06_LINKEDIN_INTELLIGENCE.md). Mirrors
// backend/schemas/executive.py.

export type SeniorityTier =
  | "founder"
  | "c_suite"
  | "executive"
  | "director"
  | "manager"
  | "individual"
  | "unknown";

export interface Executive {
  id: string;
  company_id: string;
  name: string;
  title: string | null;
  department: string | null;
  biography: string | null;
  responsibilities: string[] | null;
  business_priorities: string[] | null;
  technology_focus: string[] | null;
  confidence_score: number | null;

  // Derived from the title by the backend at response time, never stored.
  seniority_tier: SeniorityTier;
  seniority_label: string;
  is_decision_maker: boolean;
  is_technical: boolean;
  // True whenever seniority and department were read off the title rather
  // than stated by a source - which today is always. The UI says so
  // rather than presenting an inference as a fact.
  is_inferred: boolean;

  linkedin_url: string | null;
  // True when linkedin_url is a people-search link Scout constructed
  // rather than a profile it holds, so the link can be labelled "Find on
  // LinkedIn" instead of implying a verified match.
  profile_url_is_search: boolean;
}

export interface PathCandidate {
  executive: Executive;
  score: number;
  // Why this person is ranked here. Never empty - a ranking a user cannot
  // interrogate is one they have to redo themselves.
  reasons: string[];
}

export interface OrgMapGroup {
  department: string;
  executives: Executive[];
}

export interface ExecutiveOverview {
  executives: Executive[];
  org_map: OrgMapGroup[];
  paths: PathCandidate[];
  decision_maker_count: number;
}
