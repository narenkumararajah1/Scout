export interface Company {
  id: string;
  name: string;
  industry: string | null;
  headquarters: string | null;
  website: string | null;
  monitoring_status: string;
  // Priority 5 (soft delete/archive) - null means active; set means
  // archived. Orthogonal to monitoring_status.
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCompanyInput {
  name: string;
  industry?: string;
  headquarters?: string;
  website?: string;
}
