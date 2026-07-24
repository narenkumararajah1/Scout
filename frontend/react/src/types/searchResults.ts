// Global Search results (Priority 3). Mirrors backend/schemas/search.py.
export interface SearchCompanyResult {
  id: string;
  name: string;
  industry: string | null;
  headquarters: string | null;
  website: string | null;
  monitoring_status: string;
}

export interface SearchExecutiveResult {
  id: string;
  name: string;
  title: string | null;
  department: string | null;
  biography: string | null;
  linkedin_url: string | null;
  confidence_score: number | null;
  company_id: string;
  company_name: string | null;
}

export interface SearchOpportunityResult {
  id: string;
  company_id: string;
  company_name: string | null;
  title: string;
  description: string | null;
  priority: number | null;
  confidence_score: number | null;
}

export interface SearchResults {
  companies: SearchCompanyResult[];
  executives: SearchExecutiveResult[];
  opportunities: SearchOpportunityResult[];
}
