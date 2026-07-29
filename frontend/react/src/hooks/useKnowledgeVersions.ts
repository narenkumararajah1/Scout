import { useQuery } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";

export function useKnowledgeVersions(documentId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge-versions", documentId],
    queryFn: () => knowledgeService.listVersions(documentId as string),
    enabled: Boolean(documentId),
  });
}
