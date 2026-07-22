export interface Company {
  id: string;
  name: string;
  industry: string | null;
  headquarters: string | null;
  website: string | null;
  monitoring_status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateCompanyInput {
  name: string;
  industry?: string;
  headquarters?: string;
  website?: string;
}
