// Knowledge Library operations (V3 Enhancements Phase 1B). Wraps
// backend/api/routers/knowledge.py's /api/v1/knowledge/* endpoints.
//
// Every list-valued field is sent the way each endpoint expects it: the
// upload endpoint is multipart, so lists arrive as comma-separated
// strings, while the JSON-body endpoints take real arrays. That
// asymmetry lives here rather than leaking into the pages.
import { apiRequest, apiRequestData, apiUploadData } from "../api/client";
import type {
  IngestWebsiteInput,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeDocumentFilters,
  KnowledgeLibrary,
  KnowledgeSearchResult,
  KnowledgeVocabularies,
  UpdateKnowledgeMetadataInput,
  UploadKnowledgeDocumentInput,
} from "../types/knowledgeDocument";

const BASE = "/api/v1/knowledge";

function buildQuery(params: Record<string, string | boolean | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "" && value !== false) {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

// Only appends when there's something to send, so an untouched optional
// form field is omitted rather than posted as an empty string (which the
// backend would otherwise store as a real, blank value).
function appendIfPresent(form: FormData, key: string, value?: string): void {
  const trimmed = (value ?? "").trim();
  if (trimmed) {
    form.append(key, trimmed);
  }
}

export const knowledgeService = {
  async getVocabularies(): Promise<KnowledgeVocabularies> {
    return apiRequestData<KnowledgeVocabularies>(`${BASE}/categories`);
  },

  async listDocuments(filters: KnowledgeDocumentFilters = {}): Promise<KnowledgeLibrary> {
    const query = buildQuery({
      category: filters.category,
      status: filters.status,
      include_archived: filters.includeArchived,
      search: filters.search,
    });
    return apiRequestData<KnowledgeLibrary>(`${BASE}/documents${query}`);
  },

  async getDocument(documentId: string): Promise<KnowledgeDocumentDetail> {
    return apiRequestData<KnowledgeDocumentDetail>(`${BASE}/documents/${documentId}`);
  },

  async listVersions(documentId: string): Promise<KnowledgeDocument[]> {
    return apiRequestData<KnowledgeDocument[]>(`${BASE}/documents/${documentId}/versions`);
  },

  async uploadDocument(input: UploadKnowledgeDocumentInput): Promise<KnowledgeDocument> {
    const form = new FormData();
    form.append("file", input.file);
    form.append("category", input.category);
    appendIfPresent(form, "title", input.title);
    appendIfPresent(form, "description", input.description);
    appendIfPresent(form, "tags", input.tags);
    appendIfPresent(form, "industries", input.industries);
    appendIfPresent(form, "technologies", input.technologies);
    appendIfPresent(form, "related_services", input.relatedServices);
    appendIfPresent(form, "author", input.author);
    appendIfPresent(form, "replace_document_id", input.replaceDocumentId);
    return apiUploadData<KnowledgeDocument>(`${BASE}/documents/upload`, form);
  },

  async ingestWebsite(input: IngestWebsiteInput): Promise<KnowledgeDocument> {
    return apiRequestData<KnowledgeDocument>(`${BASE}/documents/website`, {
      method: "POST",
      body: {
        url: input.url,
        category: input.category,
        title: input.title || undefined,
        description: input.description || undefined,
        tags: input.tags?.length ? input.tags : undefined,
        industries: input.industries?.length ? input.industries : undefined,
        technologies: input.technologies?.length ? input.technologies : undefined,
        related_services: input.relatedServices?.length ? input.relatedServices : undefined,
      },
    });
  },

  async updateMetadata(documentId: string, input: UpdateKnowledgeMetadataInput): Promise<KnowledgeDocument> {
    return apiRequestData<KnowledgeDocument>(`${BASE}/documents/${documentId}`, {
      method: "PATCH",
      body: {
        title: input.title,
        description: input.description,
        category: input.category,
        tags: input.tags,
        industries: input.industries,
        technologies: input.technologies,
        related_services: input.relatedServices,
        author: input.author,
      },
    });
  },

  async refreshDocument(documentId: string): Promise<KnowledgeDocument> {
    return apiRequestData<KnowledgeDocument>(`${BASE}/documents/${documentId}/refresh`, { method: "POST" });
  },

  async archiveDocument(documentId: string): Promise<KnowledgeDocument> {
    return apiRequestData<KnowledgeDocument>(`${BASE}/documents/${documentId}/archive`, { method: "POST" });
  },

  async restoreDocument(documentId: string): Promise<KnowledgeDocument> {
    return apiRequestData<KnowledgeDocument>(`${BASE}/documents/${documentId}/restore`, { method: "POST" });
  },

  async deleteDocument(documentId: string): Promise<void> {
    await apiRequest<void>(`${BASE}/documents/${documentId}`, { method: "DELETE" });
  },

  // Semantic search across the whole corpus - both Library documents and
  // the curated Capability/Service/CaseStudy entities, since they share
  // one vector collection.
  async search(query: string, options: { category?: string; limit?: number } = {}): Promise<KnowledgeSearchResult> {
    const search = buildQuery({ q: query, category: options.category, limit: options.limit });
    return apiRequestData<KnowledgeSearchResult>(`${BASE}/search${search}`);
  },
};
