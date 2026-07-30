// Recently viewed companies (V3 Enhancements Phase 6 -
// docs/v3-enhancements/10_NAVIGATION_IMPROVEMENTS.md). Mirrors
// backend/schemas/company_view.py::RecentlyViewedCompany.
export interface RecentCompany {
  company_id: string;
  company_name: string;
  industry: string | null;
  last_viewed_at: string;
}
