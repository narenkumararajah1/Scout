// Visual Intelligence (V3 Enhancements Phase 5 -
// docs/v3-enhancements/09_VISUAL_INTELLIGENCE.md). Mirrors
// backend/schemas/visual_trends.py.

export interface CapturePoint {
  captured_at: string;
  signal_count: number;
  opportunity_count: number;
  capability_count: number;
  // null means the run predates executive capture (Phase 4A), not that
  // the company had none. Charts render a gap, never a zero.
  executive_count: number | null;
  change_count: number;

  leadership: number;
  hiring: number;
  technology: number;
  strategic: number;
}

export interface TechnologyCategoryCount {
  category: string;
  count: number;
}

export interface CompanyVisualTrends {
  company_id: string;
  captures: CapturePoint[];
  technology_categories: TechnologyCategoryCount[];
  signal_categories: string[];
  // False below two captures. The backend decides this so every surface
  // reaches the same conclusion from the same data.
  has_history: boolean;
  capture_count: number;
}
