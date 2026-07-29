// Knowledge Library (V3 Enhancements Phase 1B -
// docs/v3-enhancements/04_KNOWLEDGE_LIBRARY.md). Mirrors
// backend/schemas/knowledge_document.py.
//
// Field names stay snake_case to match the API payload verbatim, as the
// rest of this directory does (see report.ts, notification.ts) - the
// only camelCase shapes are the *Input types below, which are the
// frontend's own form state rather than API responses.

export type KnowledgeDocumentStatus = "processing" | "ready" | "archived" | "failed" | "requires_refresh";

export type KnowledgeSourceType = "upload" | "website" | "local_directory";

export interface KnowledgeDocument {
  id: string;
  title: string;
  description: string | null;
  category: string;
  source_type: KnowledgeSourceType;
  source_ref: string;
  file_type: string | null;
  file_size_bytes: number | null;
  status: KnowledgeDocumentStatus;
  status_detail: string | null;
  version: number;
  supersedes_id: string | null;
  author: string | null;
  published_at: string | null;
  tags: string[] | null;
  industries: string[] | null;
  technologies: string[] | null;
  related_services: string[] | null;
  chunk_count: number;
  last_indexed_at: string | null;
  last_refreshed_at: string | null;
  created_at: string;
  updated_at: string;
}

// The detail endpoint adds a bounded text preview so a document can be
// reviewed without downloading it.
export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  content_preview: string | null;
  content_truncated: boolean;
}

export interface KnowledgeLibrarySummary {
  total_documents: number;
  ready: number;
  processing: number;
  failed: number;
  archived: number;
  total_chunks: number;
  categories_in_use: string[];
  last_indexed_at: string | null;
}

export interface KnowledgeLibrary {
  summary: KnowledgeLibrarySummary;
  documents: KnowledgeDocument[];
}

export interface KnowledgeVocabularies {
  categories: string[];
  statuses: KnowledgeDocumentStatus[];
}

// One retrieved passage. Shared by the Library's semantic search and by
// Ask Scout's citations - both come from the same backend schema
// (KnowledgeReferenceOut), so they are typed once here.
export interface KnowledgeReference {
  content: string;
  entity_type: string | null;
  name: string | null;
  label: string | null;
  source: string | null;
  document_id: string | null;
  category: string | null;
  relevance: number | null;
}

export interface KnowledgeSearchResult {
  query: string;
  results: KnowledgeReference[];
}

export interface KnowledgeDocumentFilters {
  category?: string;
  status?: string;
  includeArchived?: boolean;
  search?: string;
}

export interface UploadKnowledgeDocumentInput {
  file: File;
  category: string;
  title?: string;
  description?: string;
  // Comma-separated in the form; the service forwards them as-is because
  // the upload endpoint is multipart and parses lists from strings.
  tags?: string;
  industries?: string;
  technologies?: string;
  relatedServices?: string;
  author?: string;
  // Set to publish a new version of an existing document rather than
  // creating a separate entry.
  replaceDocumentId?: string;
}

export interface IngestWebsiteInput {
  url: string;
  category: string;
  title?: string;
  description?: string;
  tags?: string[];
  industries?: string[];
  technologies?: string[];
  relatedServices?: string[];
}

export interface UpdateKnowledgeMetadataInput {
  title?: string;
  description?: string;
  category?: string;
  tags?: string[];
  industries?: string[];
  technologies?: string[];
  relatedServices?: string[];
  author?: string;
}
