// Mirrors backend/schemas/company_intelligence.py's CompanyIntelligenceResponse
// (V3 Phase 7A). The nested `company` shape intentionally omits
// created_at/updated_at - the backend's CompanyOut schema doesn't
// include them either, unlike the full Company type in ./company.ts.

export interface IntelligenceCompany {
  id: string;
  name: string;
  industry: string | null;
  headquarters: string | null;
  website: string | null;
  monitoring_status: string;
}

export interface Technology {
  id: string;
  name: string;
  category: string | null;
  adoption_status: string | null;
  business_relevance: string | null;
  confidence_score: number | null;
  source: string | null;
}

export interface BusinessInitiative {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  priority: number | null;
  status: string | null;
  confidence_score: number | null;
}

export interface Executive {
  id: string;
  name: string;
  title: string | null;
  department: string | null;
  biography: string | null;
  linkedin_url: string | null;
  confidence_score: number | null;
}

export interface Signal {
  id: string;
  type: string;
  title: string;
  description: string | null;
  source: string | null;
  confidence: number | null;
  date_detected: string;
}

export interface GleanKnowledgeItem {
  source: string;
  content: string;
  category: string | null;
}

export interface CompanyIntelligence {
  company: IntelligenceCompany;
  technologies: Technology[];
  business_initiatives: BusinessInitiative[];
  executives: Executive[];
  recent_signals: Signal[];
  glean_knowledge: GleanKnowledgeItem[];
}
