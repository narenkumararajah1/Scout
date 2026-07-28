// Mirrors backend/schemas/company_relationship.py exactly (roadmap
// Phase 6 - Relationship Intelligence, basic level).

export type RelationshipType = "competitor" | "partner" | "subsidiary" | "parent" | "customer";

export const RELATIONSHIP_TYPES: RelationshipType[] = [
  "competitor",
  "partner",
  "subsidiary",
  "parent",
  "customer",
];

export interface CompanyRelationship {
  id: string;
  company_id: string;
  related_company_id: string | null;
  related_company_name: string | null;
  relationship_type: RelationshipType;
  notes: string | null;
  created_at: string;
}

export interface CreateCompanyRelationshipInput {
  relationshipType: RelationshipType;
  relatedCompanyId?: string;
  relatedCompanyName?: string;
  notes?: string;
}
