import { useQuery } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";

// Semantic search costs an embedding of the query, so this only runs for
// a submitted query - the page holds the input's draft state itself and
// passes the query through on submit rather than on every keystroke.
export function useKnowledgeSearch(query: string, options: { category?: string; limit?: number } = {}) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: ["knowledge-search", trimmed, options.category, options.limit],
    queryFn: () => knowledgeService.search(trimmed, options),
    enabled: trimmed.length > 0,
  });
}
