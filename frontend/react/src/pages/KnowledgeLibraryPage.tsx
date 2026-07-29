// Knowledge Library (V3 Enhancements Phase 1B -
// docs/v3-enhancements/04_KNOWLEDGE_LIBRARY.md). The transparent view of
// what Scout actually knows: browse, search, upload, and monitor
// ingestion status.
//
// Semantic search is deliberately separate from the catalog's keyword
// filter, because they answer different questions. The filter narrows
// the list of documents by title/description substring; the search
// returns individual passages ranked by meaning, across both uploaded
// documents and the curated Capability/CaseStudy entities. Collapsing
// them into one box would make it impossible to tell which one produced
// a given result.
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useKnowledgeActions } from "../hooks/useKnowledgeActions";
import { useKnowledgeDocuments } from "../hooks/useKnowledgeDocuments";
import { useKnowledgeSearch } from "../hooks/useKnowledgeSearch";
import { useKnowledgeVocabularies } from "../hooks/useKnowledgeVocabularies";
import { useToasts } from "../hooks/useToasts";
import { getErrorMessage } from "../utils/errors";
import {
  formatFileSize,
  formatKnowledgeLabel,
  formatSourceType,
  formatTimestamp,
  knowledgeStatusVariant,
  parseCommaSeparated,
} from "../utils/knowledgeDocument";

const SEARCH_RESULT_LIMIT = 10;

export function KnowledgeLibraryPage() {
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [appliedFilterText, setAppliedFilterText] = useState("");

  const [searchDraft, setSearchDraft] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadCategory, setUploadCategory] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadTags, setUploadTags] = useState("");
  const [uploadIndustries, setUploadIndustries] = useState("");

  const [websiteUrl, setWebsiteUrl] = useState("");
  const [websiteCategory, setWebsiteCategory] = useState("");
  const [websiteIndustries, setWebsiteIndustries] = useState("");

  const vocabularies = useKnowledgeVocabularies();
  const library = useKnowledgeDocuments({
    category: category || undefined,
    status: status || undefined,
    includeArchived,
    search: appliedFilterText || undefined,
  });
  const search = useKnowledgeSearch(searchQuery, { limit: SEARCH_RESULT_LIMIT });
  const { uploadDocument, ingestWebsite } = useKnowledgeActions();
  const { toasts, pushToast, dismissToast } = useToasts();

  const categories = vocabularies.data?.categories ?? [];
  const statuses = vocabularies.data?.statuses ?? [];
  const summary = library.data?.summary;
  const documents = library.data?.documents ?? [];

  function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!uploadFile || !uploadCategory) {
      pushToast("Choose a file and a category before uploading.", "error");
      return;
    }
    uploadDocument.mutate(
      {
        file: uploadFile,
        category: uploadCategory,
        title: uploadTitle,
        tags: uploadTags,
        industries: uploadIndustries,
      },
      {
        onSuccess: (document) => {
          pushToast(`"${document.title}" ingested into ${document.chunk_count} searchable passages.`, "success");
          setUploadFile(null);
          setUploadTitle("");
          setUploadTags("");
          setUploadIndustries("");
          // The file input is uncontrolled (a File cannot be set as a
          // value), so it is reset through the form element itself.
          (event.target as HTMLFormElement).reset();
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  function handleIngestWebsite(event: React.FormEvent) {
    event.preventDefault();
    if (!websiteUrl || !websiteCategory) {
      pushToast("Enter a URL and choose a category before ingesting.", "error");
      return;
    }
    ingestWebsite.mutate(
      {
        url: websiteUrl,
        category: websiteCategory,
        industries: parseCommaSeparated(websiteIndustries),
      },
      {
        onSuccess: (document) => {
          pushToast(`"${document.title}" ingested into ${document.chunk_count} searchable passages.`, "success");
          setWebsiteUrl("");
          setWebsiteIndustries("");
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  return (
    <div className="knowledge-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <h1>Knowledge Library</h1>
      <p className="card-description">
        Everything Scout knows about Innominds. Every AI recommendation is grounded in these documents.
      </p>

      {summary && (
        <div className="knowledge-summary">
          <div className="knowledge-stat">
            <span className="knowledge-stat-value">{summary.total_documents}</span>
            <span className="knowledge-stat-label">Documents</span>
          </div>
          <div className="knowledge-stat">
            <span className="knowledge-stat-value">{summary.ready}</span>
            <span className="knowledge-stat-label">Ready</span>
          </div>
          {summary.processing > 0 && (
            <div className="knowledge-stat">
              <span className="knowledge-stat-value">{summary.processing}</span>
              <span className="knowledge-stat-label">Processing</span>
            </div>
          )}
          {summary.failed > 0 && (
            <div className="knowledge-stat knowledge-stat-alert">
              <span className="knowledge-stat-value">{summary.failed}</span>
              <span className="knowledge-stat-label">Failed</span>
            </div>
          )}
          {summary.archived > 0 && (
            <div className="knowledge-stat">
              <span className="knowledge-stat-value">{summary.archived}</span>
              <span className="knowledge-stat-label">Archived</span>
            </div>
          )}
          <div className="knowledge-stat">
            <span className="knowledge-stat-value">{summary.total_chunks}</span>
            <span className="knowledge-stat-label">Searchable passages</span>
          </div>
        </div>
      )}

      <Card title="Search Scout's knowledge">
        <form
          className="knowledge-search-form"
          onSubmit={(event) => {
            event.preventDefault();
            setSearchQuery(searchDraft);
          }}
        >
          <input
            type="search"
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="e.g. healthcare claims platform modernization"
            aria-label="Search Scout's knowledge"
          />
          <button type="submit" disabled={!searchDraft.trim()}>
            Search
          </button>
          {searchQuery && (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setSearchQuery("");
                setSearchDraft("");
              }}
            >
              Clear
            </button>
          )}
        </form>
        <p className="knowledge-hint">
          Ranked by meaning, not keywords. Covers uploaded documents and Scout's curated capabilities and case
          studies.
        </p>

        {searchQuery &&
          (search.isLoading ? (
            <LoadingState message="Searching..." />
          ) : search.isError ? (
            <ErrorState message={getErrorMessage(search.error)} onRetry={() => void search.refetch()} />
          ) : (search.data?.results.length ?? 0) === 0 ? (
            <EmptyState message="No passages matched that query." />
          ) : (
            <ul className="knowledge-search-results">
              {search.data?.results.map((reference, index) => (
                <li key={`${reference.source ?? "result"}-${index}`} className="knowledge-search-result">
                  <div className="knowledge-search-result-header">
                    <span className="knowledge-search-result-label">{reference.label ?? "Knowledge"}</span>
                    {reference.relevance !== null && (
                      <Badge label={`${Math.round(reference.relevance * 100)}% match`} />
                    )}
                    {reference.document_id && (
                      <Link to={`/knowledge/${reference.document_id}`}>View document</Link>
                    )}
                  </div>
                  <p className="knowledge-search-result-content">{reference.content}</p>
                </li>
              ))}
            </ul>
          ))}
      </Card>

      <div className="knowledge-ingest-grid">
        <Card title="Upload a document">
          <form className="knowledge-form" onSubmit={handleUpload}>
            <label>
              File
              <input
                type="file"
                accept=".pdf,.txt,.md,.markdown,.html,.htm"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            <label>
              Category
              <select value={uploadCategory} onChange={(event) => setUploadCategory(event.target.value)} required>
                <option value="">Select a category</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {formatKnowledgeLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Title <span className="knowledge-optional">optional</span>
              <input
                type="text"
                value={uploadTitle}
                onChange={(event) => setUploadTitle(event.target.value)}
                placeholder="Taken from the document if left blank"
              />
            </label>
            <label>
              Tags <span className="knowledge-optional">comma separated</span>
              <input
                type="text"
                value={uploadTags}
                onChange={(event) => setUploadTags(event.target.value)}
                placeholder="kubernetes, aws, migration"
              />
            </label>
            <label>
              Industries <span className="knowledge-optional">comma separated</span>
              <input
                type="text"
                value={uploadIndustries}
                onChange={(event) => setUploadIndustries(event.target.value)}
                placeholder="Healthcare, Financial Services"
              />
            </label>
            <button type="submit" disabled={uploadDocument.isPending}>
              {uploadDocument.isPending ? "Ingesting..." : "Upload and index"}
            </button>
            <p className="knowledge-hint">PDF, text, Markdown, or HTML. Scanned PDFs need OCR first.</p>
          </form>
        </Card>

        <Card title="Ingest a web page">
          <form className="knowledge-form" onSubmit={handleIngestWebsite}>
            <label>
              URL
              <input
                type="url"
                value={websiteUrl}
                onChange={(event) => setWebsiteUrl(event.target.value)}
                placeholder="https://www.innominds.com/enterprise-ai"
                required
              />
            </label>
            <label>
              Category
              <select value={websiteCategory} onChange={(event) => setWebsiteCategory(event.target.value)} required>
                <option value="">Select a category</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {formatKnowledgeLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Industries <span className="knowledge-optional">comma separated</span>
              <input
                type="text"
                value={websiteIndustries}
                onChange={(event) => setWebsiteIndustries(event.target.value)}
                placeholder="Healthcare, Manufacturing"
              />
            </label>
            <button type="submit" disabled={ingestWebsite.isPending}>
              {ingestWebsite.isPending ? "Fetching..." : "Fetch and index"}
            </button>
            <p className="knowledge-hint">
              Re-ingesting the same URL updates it in place, and creates a new version only when the page has
              changed.
            </p>
          </form>
        </Card>
      </div>

      <Card title="Documents">
        <div className="knowledge-filters">
          <label>
            Category
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">All categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {formatKnowledgeLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All statuses</option>
              {statuses.map((item) => (
                <option key={item} value={item}>
                  {formatKnowledgeLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <form
            className="knowledge-filter-text"
            onSubmit={(event) => {
              event.preventDefault();
              setAppliedFilterText(filterText);
            }}
          >
            <label>
              Title or description
              <input
                type="search"
                value={filterText}
                onChange={(event) => setFilterText(event.target.value)}
                placeholder="Filter by name"
              />
            </label>
            <button type="submit">Apply</button>
          </form>
          <label className="knowledge-archived-toggle">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(event) => setIncludeArchived(event.target.checked)}
            />
            Include archived
          </label>
        </div>

        {library.isLoading ? (
          <LoadingState />
        ) : library.isError ? (
          <ErrorState message={getErrorMessage(library.error)} onRetry={() => void library.refetch()} />
        ) : documents.length === 0 ? (
          <EmptyState
            message={
              appliedFilterText || category || status
                ? "No documents match these filters."
                : "No knowledge yet. Upload a case study or ingest a service page to get started."
            }
          />
        ) : (
          <ul className="knowledge-document-list">
            {documents.map((document) => (
              <li key={document.id} className="knowledge-document-item">
                <div className="knowledge-document-main">
                  <Link to={`/knowledge/${document.id}`} className="knowledge-document-title">
                    {document.title}
                  </Link>
                  <div className="knowledge-document-badges">
                    <Badge label={formatKnowledgeLabel(document.status)} variant={knowledgeStatusVariant(document.status)} />
                    <Badge label={formatKnowledgeLabel(document.category)} />
                    {document.version > 1 && <Badge label={`v${document.version}`} />}
                  </div>
                  {document.description && <p className="knowledge-document-description">{document.description}</p>}
                  {document.status === "failed" && document.status_detail && (
                    <p className="knowledge-document-failure">{document.status_detail}</p>
                  )}
                </div>
                <dl className="knowledge-document-meta">
                  <div>
                    <dt>Source</dt>
                    <dd>{formatSourceType(document.source_type)}</dd>
                  </div>
                  <div>
                    <dt>Passages</dt>
                    <dd>{document.chunk_count}</dd>
                  </div>
                  <div>
                    <dt>Size</dt>
                    <dd>{formatFileSize(document.file_size_bytes)}</dd>
                  </div>
                  <div>
                    <dt>Indexed</dt>
                    <dd>{formatTimestamp(document.last_indexed_at)}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
