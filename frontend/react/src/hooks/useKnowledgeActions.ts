import { useMutation, useQueryClient } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";
import type {
  IngestWebsiteInput,
  UpdateKnowledgeMetadataInput,
  UploadKnowledgeDocumentInput,
} from "../types/knowledgeDocument";

// Every mutation here changes both the catalog row and the underlying
// vectors, so the whole knowledge query space is invalidated rather than
// individual keys: a metadata edit re-indexes chunks, an archive removes
// them, and a stale search result would otherwise still show passages
// from a document that is no longer retrievable.
export function useKnowledgeActions() {
  const queryClient = useQueryClient();

  function invalidateAll() {
    void queryClient.invalidateQueries({ queryKey: ["knowledge-documents"] });
    void queryClient.invalidateQueries({ queryKey: ["knowledge-search"] });
  }

  function invalidateDocument(documentId: string) {
    void queryClient.invalidateQueries({ queryKey: ["knowledge-document", documentId] });
    void queryClient.invalidateQueries({ queryKey: ["knowledge-versions", documentId] });
    invalidateAll();
  }

  const uploadDocument = useMutation({
    mutationFn: (input: UploadKnowledgeDocumentInput) => knowledgeService.uploadDocument(input),
    onSuccess: invalidateAll,
  });

  const ingestWebsite = useMutation({
    mutationFn: (input: IngestWebsiteInput) => knowledgeService.ingestWebsite(input),
    onSuccess: invalidateAll,
  });

  const updateMetadata = useMutation({
    mutationFn: ({ documentId, input }: { documentId: string; input: UpdateKnowledgeMetadataInput }) =>
      knowledgeService.updateMetadata(documentId, input),
    onSuccess: (_data, variables) => invalidateDocument(variables.documentId),
  });

  const refreshDocument = useMutation({
    mutationFn: (documentId: string) => knowledgeService.refreshDocument(documentId),
    onSuccess: (_data, documentId) => invalidateDocument(documentId),
  });

  const archiveDocument = useMutation({
    mutationFn: (documentId: string) => knowledgeService.archiveDocument(documentId),
    onSuccess: (_data, documentId) => invalidateDocument(documentId),
  });

  const restoreDocument = useMutation({
    mutationFn: (documentId: string) => knowledgeService.restoreDocument(documentId),
    onSuccess: (_data, documentId) => invalidateDocument(documentId),
  });

  const deleteDocument = useMutation({
    mutationFn: (documentId: string) => knowledgeService.deleteDocument(documentId),
    onSuccess: invalidateAll,
  });

  return {
    uploadDocument,
    ingestWebsite,
    updateMetadata,
    refreshDocument,
    archiveDocument,
    restoreDocument,
    deleteDocument,
  };
}
