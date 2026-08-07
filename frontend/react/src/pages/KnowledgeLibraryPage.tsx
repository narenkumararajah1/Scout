// Knowledge Library - the workspace where Scout's knowledge is managed.
//
// The four things this page exists to do are adding documents, ingesting
// web pages, browsing what is there, and searching it. Those come first
// and stay visible.
//
// Coverage analysis sits underneath them and serves them. It is not a
// case for Scout's trustworthiness; it is the answer to "what should I
// upload next". It starts from the services Scout actually recommends
// (ExecutiveDashboard.recommended_services), asks the memory what real
// project evidence stands behind each, and ranks the shortfalls by how
// many accounts are riding on them. Acting on a row drops you into the
// upload form with the category and tag already set, which is the whole
// point of keeping it on this page rather than in Analytics.
//
// The join is made at read time because no persisted document ->
// opportunity edge exists in the schema; see useServiceEvidence.
import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BulkIngestPanel } from "../components/knowledge/BulkIngestPanel";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useExecutiveDashboard } from "../hooks/useExecutiveDashboard";
import { useKnowledgeActions } from "../hooks/useKnowledgeActions";
import { useKnowledgeDocuments } from "../hooks/useKnowledgeDocuments";
import { useKnowledgeSearch } from "../hooks/useKnowledgeSearch";
import { useKnowledgeVocabularies } from "../hooks/useKnowledgeVocabularies";
import { useServiceEvidence, type ServiceEvidence } from "../hooks/useServiceEvidence";
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
const DASHBOARD_LIMIT = 50;
const SCALE_PADDING = 0.02;
// The category that evidence for a service belongs in, used when the
// coverage panel hands a shortfall over to the upload form.
const EVIDENCE_CATEGORY = "case_studies";

type IngestMode = "upload" | "bulk" | "website";
type EvidenceBand = "strong" | "mixed" | "thin";

const INGEST_TABS: { id: IngestMode; label: string }[] = [
  { id: "upload", label: "Upload a document" },
  { id: "bulk", label: "Bulk import" },
  { id: "website", label: "Ingest a web page" },
];

const BAND_LABEL: Record<EvidenceBand, string> = {
  strong: "Well evidenced",
  mixed: "Partly evidenced",
  thin: "Thinly evidenced",
};

interface ServiceDemand {
  service: string;
  companies: string[];
}

interface CoverageRow extends ServiceEvidence {
  companies: string[];
  band: EvidenceBand | null;
  exposure: number | null;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

// Relative to the spread actually observed rather than fixed cutoffs: a
// similarity score has no absolute meaning, but "furthest from its own
// capability statement, among these" does.
function bandOf(gap: number, allGaps: number[]): EvidenceBand {
  const min = Math.min(...allGaps);
  const max = Math.max(...allGaps);
  const span = max - min;
  if (span <= 0) {
    return "mixed";
  }
  const position = (gap - min) / span;
  if (position <= 1 / 3) {
    return "strong";
  }
  if (position <= 2 / 3) {
    return "mixed";
  }
  return "thin";
}

export function KnowledgeLibraryPage() {
  const ingestRef = useRef<HTMLElement | null>(null);
  const [ingestMode, setIngestMode] = useState<IngestMode>("upload");

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

  const [openService, setOpenService] = useState<string | null>(null);

  const dashboard = useExecutiveDashboard(DASHBOARD_LIMIT);
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

  const summary = library.data?.summary;
  const categories = vocabularies.data?.categories ?? [];
  const statuses = vocabularies.data?.statuses ?? [];
  const documents = library.data?.documents ?? [];

  const demand = useMemo<ServiceDemand[]>(() => {
    const byService = new Map<string, Set<string>>();
    for (const company of dashboard.data?.companies ?? []) {
      for (const opportunity of company.opportunities) {
        for (const service of opportunity.recommended_services) {
          const entry = byService.get(service) ?? new Set<string>();
          entry.add(company.company_name);
          byService.set(service, entry);
        }
      }
    }
    return [...byService.entries()]
      .map(([service, companies]) => ({ service, companies: [...companies].sort() }))
      .sort((a, b) => b.companies.length - a.companies.length || a.service.localeCompare(b.service));
  }, [dashboard.data]);

  const services = useMemo(() => demand.map((item) => item.service), [demand]);
  const { evidence, settledCount, isSettled } = useServiceEvidence(services);

  // Ordered by what to fix first: the shortfall weighted by how many
  // accounts the recommendation is staked on.
  const coverage = useMemo<CoverageRow[]>(() => {
    const gaps = evidence.map((item) => item.gap).filter((gap): gap is number => gap !== null);
    return demand
      .map((item, index) => {
        const found = evidence[index];
        const gap = found?.gap ?? null;
        return {
          ...found,
          companies: item.companies,
          band: gap !== null && gaps.length > 0 ? bandOf(gap, gaps) : null,
          exposure: gap !== null ? gap * item.companies.length : null,
        };
      })
      .sort((a, b) => (b.exposure ?? -1) - (a.exposure ?? -1));
  }, [demand, evidence]);

  const scale = useMemo(() => {
    const scores = coverage.flatMap((row) =>
      [row.claimRelevance, row.strongestProof].filter((value): value is number => value !== null),
    );
    if (scores.length === 0) {
      return null;
    }
    const floor = Math.min(...scores) - SCALE_PADDING;
    const ceiling = Math.max(...scores) + SCALE_PADDING;
    return { floor, ceiling, span: Math.max(ceiling - floor, 0.0001) };
  }, [coverage]);

  const positionOf = (value: number): number =>
    scale ? ((value - scale.floor) / scale.span) * 100 : 0;

  const thinCount = isSettled ? coverage.filter((row) => row.band === "thin").length : null;

  // The coverage panel's whole reason for living on this page: hand a
  // shortfall to the upload form, already pointed at the right category
  // and tagged with the service it is meant to cover.
  function addEvidenceFor(service: string) {
    setIngestMode("upload");
    setUploadCategory(categories.includes(EVIDENCE_CATEGORY) ? EVIDENCE_CATEGORY : "");
    setUploadTags(service);
    ingestRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    pushToast(`Upload a case study covering "${service}".`, "success");
  }

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
    <div className="knowledge-workspace">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <header className="kw-head">
        <div className="kw-head-text">
          <h1>Knowledge Library</h1>
          <p className="kw-lede">
            Everything Scout knows about Innominds. Every recommendation it makes is grounded in these documents.
          </p>
        </div>

        {summary && (
          <dl className="kw-stats">
            <div className="kw-stat">
              <dt>Documents</dt>
              <dd>{summary.total_documents}</dd>
            </div>
            <div className="kw-stat">
              <dt>Searchable passages</dt>
              <dd>{summary.total_chunks}</dd>
            </div>
            <div className={`kw-stat${summary.failed > 0 ? " kw-stat-alert" : ""}`}>
              <dt>{summary.failed > 0 ? "Failed to index" : "Indexed"}</dt>
              <dd>{summary.failed > 0 ? summary.failed : summary.ready}</dd>
            </div>
            {summary.processing > 0 && (
              <div className="kw-stat">
                <dt>Processing</dt>
                <dd>{summary.processing}</dd>
              </div>
            )}
            <div className="kw-stat">
              <dt>Last indexed</dt>
              <dd className="kw-stat-when">{formatTimestamp(summary.last_indexed_at)}</dd>
            </div>
          </dl>
        )}
      </header>

      {/* --- add to the library ------------------------------------------ */}
      <section className="kw-panel kw-ingest" ref={ingestRef} aria-label="Add to the library">
        <div className="kw-panel-head">
          <h2>Add to the library</h2>
          <div className="kw-tabs" role="tablist" aria-label="How to add knowledge">
            {INGEST_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={ingestMode === tab.id}
                className={`kw-tab${ingestMode === tab.id ? " active" : ""}`}
                onClick={() => setIngestMode(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {ingestMode === "upload" && (
          <form className="kw-form" onSubmit={handleUpload}>
            <div className="kw-field kw-field-wide">
              <label htmlFor="kw-file">File</label>
              <input
                id="kw-file"
                type="file"
                accept=".pdf,.txt,.md,.markdown,.html,.htm"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                required
              />
            </div>
            <div className="kw-field">
              <label htmlFor="kw-category">Category</label>
              <select
                id="kw-category"
                value={uploadCategory}
                onChange={(event) => setUploadCategory(event.target.value)}
                required
              >
                <option value="">Select a category</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {formatKnowledgeLabel(item)}
                  </option>
                ))}
              </select>
            </div>
            <div className="kw-field">
              <label htmlFor="kw-title">
                Title <span className="kw-optional">optional</span>
              </label>
              <input
                id="kw-title"
                type="text"
                value={uploadTitle}
                onChange={(event) => setUploadTitle(event.target.value)}
                placeholder="Taken from the document if left blank"
              />
            </div>
            <div className="kw-field">
              <label htmlFor="kw-tags">
                Tags <span className="kw-optional">comma separated</span>
              </label>
              <input
                id="kw-tags"
                type="text"
                value={uploadTags}
                onChange={(event) => setUploadTags(event.target.value)}
                placeholder="kubernetes, aws, migration"
              />
            </div>
            <div className="kw-field">
              <label htmlFor="kw-industries">
                Industries <span className="kw-optional">comma separated</span>
              </label>
              <input
                id="kw-industries"
                type="text"
                value={uploadIndustries}
                onChange={(event) => setUploadIndustries(event.target.value)}
                placeholder="Healthcare, Financial Services"
              />
            </div>
            <div className="kw-form-actions">
              <button type="submit" disabled={uploadDocument.isPending}>
                {uploadDocument.isPending ? "Ingesting..." : "Upload and index"}
              </button>
              <p className="kw-hint">PDF, text, Markdown, or HTML. Scanned PDFs need OCR first.</p>
            </div>
          </form>
        )}

        {ingestMode === "bulk" && (
          <BulkIngestPanel categories={categories} onComplete={() => library.refetch()} />
        )}

        {ingestMode === "website" && (
          <form className="kw-form" onSubmit={handleIngestWebsite}>
            <div className="kw-field kw-field-wide">
              <label htmlFor="kw-url">URL</label>
              <input
                id="kw-url"
                type="url"
                value={websiteUrl}
                onChange={(event) => setWebsiteUrl(event.target.value)}
                placeholder="https://www.innominds.com/enterprise-ai"
                required
              />
            </div>
            <div className="kw-field">
              <label htmlFor="kw-web-category">Category</label>
              <select
                id="kw-web-category"
                value={websiteCategory}
                onChange={(event) => setWebsiteCategory(event.target.value)}
                required
              >
                <option value="">Select a category</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {formatKnowledgeLabel(item)}
                  </option>
                ))}
              </select>
            </div>
            <div className="kw-field">
              <label htmlFor="kw-web-industries">
                Industries <span className="kw-optional">comma separated</span>
              </label>
              <input
                id="kw-web-industries"
                type="text"
                value={websiteIndustries}
                onChange={(event) => setWebsiteIndustries(event.target.value)}
                placeholder="Healthcare, Manufacturing"
              />
            </div>
            <div className="kw-form-actions">
              <button type="submit" disabled={ingestWebsite.isPending}>
                {ingestWebsite.isPending ? "Fetching..." : "Fetch and index"}
              </button>
              <p className="kw-hint">
                Re-ingesting the same URL updates it in place, and creates a new version only when the page has
                changed.
              </p>
            </div>
          </form>
        )}
      </section>

      {/* --- search ------------------------------------------------------- */}
      <section className="kw-panel kw-search" aria-label="Search the knowledge base">
        <div className="kw-panel-head">
          <h2>Search the knowledge base</h2>
          <p className="kw-hint">
            Ranked by meaning, not keywords. Covers ingested documents and Scout&rsquo;s curated capabilities.
          </p>
        </div>

        <form
          className="kw-search-form"
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
            aria-label="Search the knowledge base"
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

        {searchQuery &&
          (search.isLoading ? (
            <LoadingState message="Searching..." />
          ) : search.isError ? (
            <ErrorState message={getErrorMessage(search.error)} onRetry={() => void search.refetch()} />
          ) : (search.data?.results.length ?? 0) === 0 ? (
            <EmptyState message="No passages matched that query." />
          ) : (
            <ul className="kw-results">
              {search.data?.results.map((reference, index) => (
                <li key={`${reference.source ?? "result"}-${index}`} className="kw-result">
                  <div className="kw-result-head">
                    <span className="kw-result-kind">
                      {formatKnowledgeLabel(reference.entity_type ?? "knowledge")}
                    </span>
                    <span className="kw-result-name">{reference.name ?? "Knowledge"}</span>
                    {reference.relevance !== null && (
                      <span className="kw-result-match">{percent(reference.relevance)}</span>
                    )}
                    {reference.document_id && (
                      <Link to={`/knowledge/${reference.document_id}`} className="kw-result-link">
                        Open
                      </Link>
                    )}
                  </div>
                  <p className="kw-result-content">{reference.content}</p>
                </li>
              ))}
            </ul>
          ))}
      </section>

      {/* --- browse ------------------------------------------------------- */}
      <section className="kw-panel kw-browse" aria-label="Browse documents">
        <div className="kw-panel-head">
          <h2>
            Documents
            {summary && <span className="kw-count">{summary.total_documents}</span>}
          </h2>
        </div>

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
                    <Badge
                      label={formatKnowledgeLabel(document.status)}
                      variant={knowledgeStatusVariant(document.status)}
                    />
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
      </section>

      {/* --- coverage: what to add next ----------------------------------- */}
      {services.length > 0 && (
        <section className="kw-panel kw-coverage" aria-label="Coverage gaps">
          <div className="kw-panel-head">
            <h2>Where the library is thin</h2>
            <p className="kw-hint">
              {isSettled ? (
                <>
                  Scout recommends {services.length} services across the portfolio.{" "}
                  {thinCount === 0
                    ? "Each one has a comparable project behind it."
                    : `${thinCount} ${thinCount === 1 ? "has" : "have"} no close project behind ${
                        thinCount === 1 ? "it" : "them"
                      } — the widest shortfalls first.`}
                </>
              ) : (
                <>
                  Checking each service Scout recommends against the library &mdash; {settledCount} of{" "}
                  {services.length}
                </>
              )}
            </p>
          </div>

          <ol className={`ledger${openService ? " ledger-focused" : ""}`}>
            {coverage.map((row) => {
              const isOpen = openService === row.service;
              const hasScores = row.claimRelevance !== null && row.strongestProof !== null && scale !== null;

              return (
                <li
                  key={row.service}
                  className={`ledger-row${isOpen ? " open" : ""}${row.band ? ` band-${row.band}` : ""}`}
                >
                  <button
                    type="button"
                    className="ledger-summary"
                    aria-expanded={isOpen}
                    onClick={() => setOpenService(isOpen ? null : row.service)}
                  >
                    <span className="ledger-name">{row.service}</span>

                    <span className="ledger-demand">
                      <span className="ledger-demand-count">{row.companies.length}</span>
                      <span className="ledger-demand-unit">
                        compan{row.companies.length === 1 ? "y" : "ies"}
                      </span>
                    </span>

                    <span className="ledger-track">
                      {row.isLoading ? (
                        <span className="ledger-track-waiting" />
                      ) : row.isError ? (
                        <span className="ledger-track-error">Search unavailable</span>
                      ) : hasScores ? (
                        <>
                          <span
                            className="ledger-span"
                            style={{
                              left: `${positionOf(row.strongestProof as number)}%`,
                              width: `${
                                positionOf(row.claimRelevance as number) -
                                positionOf(row.strongestProof as number)
                              }%`,
                            }}
                          />
                          <span
                            className="ledger-mark ledger-mark-proof"
                            style={{ left: `${positionOf(row.strongestProof as number)}%` }}
                          >
                            <span className="ledger-mark-value">{percent(row.strongestProof as number)}</span>
                          </span>
                          <span
                            className="ledger-mark ledger-mark-claim"
                            style={{ left: `${positionOf(row.claimRelevance as number)}%` }}
                          >
                            <span className="ledger-mark-value">{percent(row.claimRelevance as number)}</span>
                          </span>
                        </>
                      ) : (
                        <span className="ledger-track-empty">Nothing comparable</span>
                      )}
                    </span>

                    <span className="ledger-verdict">
                      {row.band ? BAND_LABEL[row.band] : row.isLoading ? "" : "No evidence"}
                      {/* The band comes from the gap, not the proof score, so
                          the gap has to be on screen - otherwise a row at 79%
                          reads as better evidenced than one at 82% with no
                          explanation. */}
                      {row.gap !== null && (
                        <span className="ledger-gap">{Math.round(row.gap * 100)} pts short</span>
                      )}
                    </span>
                  </button>

                  <div className="ledger-detail" aria-hidden={!isOpen}>
                    <div className="ledger-detail-inner">
                      {row.claim?.content && (
                        <div className="ledger-claim-block">
                          <p className="ledger-block-label">The capability Scout states</p>
                          <p className="ledger-claim-text">{row.claim.content}</p>
                        </div>
                      )}

                      <div className="ledger-proof-block">
                        <p className="ledger-block-label">
                          Closest documents in the library
                          {row.proof.length > 0 && (
                            <span className="ledger-block-count">
                              {row.proof.length} match{row.proof.length === 1 ? "" : "es"}
                            </span>
                          )}
                        </p>
                        {row.proof.length === 0 ? (
                          <p className="ledger-no-proof">
                            Nothing in the library answers to this service.
                          </p>
                        ) : (
                          <ol className="proof-list">
                            {row.proof.map((item) => (
                              <li key={item.documentId} className="proof-item">
                                <div className="proof-item-head">
                                  <Link to={`/knowledge/${item.documentId}`} className="proof-title">
                                    {item.title}
                                  </Link>
                                  <span className="proof-match">{percent(item.relevance)}</span>
                                </div>
                                <p className="proof-excerpt">{item.excerpt}</p>
                              </li>
                            ))}
                          </ol>
                        )}
                      </div>

                      <div className="ledger-foot">
                        <p className="ledger-accounts">Recommended to {row.companies.join(", ")}.</p>
                        <button
                          type="button"
                          className="ledger-action"
                          onClick={() => addEvidenceFor(row.service)}
                        >
                          Add a case study for this
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      )}
    </div>
  );
}
