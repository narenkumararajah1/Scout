import { useQuery } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";

export function useKnowledgeDocument(documentId: string | undefined) {
  return useQuery({
    queryKey: ["knowledge-document", documentId],
    queryFn: () => knowledgeService.getDocument(documentId as string),
    enabled: Boolean(documentId),
  });
}
