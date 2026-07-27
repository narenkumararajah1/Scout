// Mirrors backend/schemas/sales_coach.py's SalesCoachRecommendation
// exactly (roadmap Phase 4, item 10 - "What Would You Do?").

export interface SalesCoachRecommendation {
  who_to_contact: string | null;
  best_talking_points: string[];
  best_timing: string | null;
  risks: string[];
  suggested_sequence: string[];
  why: string | null;
}
