import { useQuery } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";

// Categories and statuses come from the backend rather than being
// duplicated here, so the filter controls can never drift from what the
// ingestion service actually validates against. They effectively never
// change at runtime, hence the long stale time.
const ONE_HOUR_MS = 60 * 60 * 1000;

export function useKnowledgeVocabularies() {
  return useQuery({
    queryKey: ["knowledge-vocabularies"],
    queryFn: () => knowledgeService.getVocabularies(),
    staleTime: ONE_HOUR_MS,
  });
}
