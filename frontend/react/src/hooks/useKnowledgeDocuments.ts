import { useQuery } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";
import type { KnowledgeDocumentFilters } from "../types/knowledgeDocument";

// Filters are part of the query key so each combination caches
// independently and switching back to a previous filter is instant.
export function useKnowledgeDocuments(filters: KnowledgeDocumentFilters = {}) {
  return useQuery({
    queryKey: ["knowledge-documents", filters],
    queryFn: () => knowledgeService.listDocuments(filters),
  });
}
