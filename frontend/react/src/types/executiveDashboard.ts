// Mirrors backend/services/analytics_service.py's executive_dashboard()
// raw dict return shape exactly (roadmap Phase 3 - Executive
// Intelligence Dashboard) - no new aggregation on the frontend.

export interface ExecutiveDashboardOpportunity {
  id: string;
  title: string;
  priority: number | null;
  confidence_score: number | null;
  recommended_services: string[];
  // Already-persisted CapabilityMatch.reasoning strings - the
  // human-readable "why this scored the way it did" explanation
  // (no new AI call made to produce these).
  reasoning: string[];
  // Signal.type -> count backing this opportunity, e.g. {"hiring": 2}.
  signal_type_counts: Record<string, number>;
}

export interface ExecutiveDashboardCompany {
  company_id: string;
  company_name: string;
  opportunities: ExecutiveDashboardOpportunity[];
}

export interface ExecutiveDashboard {
  companies: ExecutiveDashboardCompany[];
}
