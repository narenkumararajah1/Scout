// Knowledge document detail (V3 Enhancements Phase 1B -
// 04_KNOWLEDGE_LIBRARY.md's "Document View", "Metadata Management",
// "Version Management" and "Refresh").
//
// The lifecycle actions are shown according to what they actually mean
// rather than all at once: archive is the reversible "stop Scout
// retrieving this" and so is offered for an active document, restore is
// its inverse and only appears once archived, and delete is permanent so
// it always confirms first. Refresh differs by source - a web page is
// refetched, an uploaded file is re-chunked from its stored text - which
// the button's help text states, since the distinction changes whether
// new content can appear.
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useConfirm } from "../hooks/useConfirm";
import { useKnowledgeActions } from "../hooks/useKnowledgeActions";
import { useKnowledgeDocument } from "../hooks/useKnowledgeDocument";
import { useKnowledgeVersions } from "../hooks/useKnowledgeVersions";
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

export function KnowledgeDocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const documentQuery = useKnowledgeDocument(documentId);
  const versionsQuery = useKnowledgeVersions(documentId);
  const vocabularies = useKnowledgeVocabularies();
  const { updateMetadata, refreshDocument, archiveDocument, restoreDocument, deleteDocument } =
    useKnowledgeActions();
  const { toasts, pushToast, dismissToast } = useToasts();
  const { confirm, confirmDialog } = useConfirm();

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editTags, setEditTags] = useState("");
  const [editIndustries, setEditIndustries] = useState("");
  const [editTechnologies, setEditTechnologies] = useState("");

  const document = documentQuery.data;

  function startEditing() {
    if (!document) {
      return;
    }
    setEditTitle(document.title);
    setEditDescription(document.description ?? "");
    setEditCategory(document.category);
    setEditTags((document.tags ?? []).join(", "));
    setEditIndustries((document.industries ?? []).join(", "));
    setEditTechnologies((document.technologies ?? []).join(", "));
    setIsEditing(true);
  }

  function handleSaveMetadata(event: React.FormEvent) {
    event.preventDefault();
    if (!documentId) {
      return;
    }
    updateMetadata.mutate(
      {
        documentId,
        input: {
          title: editTitle,
          description: editDescription,
          category: editCategory,
          tags: parseCommaSeparated(editTags),
          industries: parseCommaSeparated(editIndustries),
          technologies: parseCommaSeparated(editTechnologies),
        },
      },
      {
        onSuccess: () => {
          pushToast("Metadata updated and passages re-indexed.", "success");
          setIsEditing(false);
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  function handleRefresh() {
    if (!documentId) {
      return;
    }
    refreshDocument.mutate(documentId, {
      onSuccess: (updated) =>
        pushToast(`Refreshed into ${updated.chunk_count} searchable passages.`, "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleArchive() {
    if (!documentId) {
      return;
    }
    archiveDocument.mutate(documentId, {
      onSuccess: () => pushToast("Archived. Scout will no longer retrieve this document.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleRestore() {
    if (!documentId) {
      return;
    }
    restoreDocument.mutate(documentId, {
      onSuccess: () => pushToast("Restored and re-indexed.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  async function handleDelete() {
    if (!documentId || !document) {
      return;
    }
    const confirmed = await confirm(
      `Permanently delete "${document.title}"? Its passages will be removed from Scout's knowledge and this cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }
    deleteDocument.mutate(documentId, {
      onSuccess: () => navigate("/knowledge"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  if (documentQuery.isLoading) {
    return <LoadingState />;
  }
  if (documentQuery.isError) {
    return (
      <ErrorState
        message={getErrorMessage(documentQuery.error)}
        onRetry={() => void documentQuery.refetch()}
      />
    );
  }
  if (!document) {
    return <EmptyState message="Document not found." />;
  }

  const isArchived = document.status === "archived";
  const versions = versionsQuery.data ?? [];
  const categories = vocabularies.data?.categories ?? [];

  return (
    <div className="knowledge-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <Link to="/knowledge" className="breadcrumb-back">
        ← Knowledge Library
      </Link>

      <div className="page-header">
        <h1>{document.title}</h1>
        <div className="knowledge-document-badges">
          <Badge label={formatKnowledgeLabel(document.status)} variant={knowledgeStatusVariant(document.status)} />
          <Badge label={formatKnowledgeLabel(document.category)} />
          <Badge label={`Version ${document.version}`} />
        </div>
      </div>

      {document.status === "failed" && document.status_detail && (
        <ErrorState message={`Ingestion failed: ${document.status_detail}`} />
      )}

      <div className="knowledge-actions">
        <button type="button" onClick={handleRefresh} disabled={refreshDocument.isPending || isArchived}>
          {refreshDocument.isPending ? "Refreshing..." : "Refresh"}
        </button>
        {isArchived ? (
          <button type="button" onClick={handleRestore} disabled={restoreDocument.isPending}>
            {restoreDocument.isPending ? "Restoring..." : "Restore"}
          </button>
        ) : (
          <button type="button" onClick={handleArchive} disabled={archiveDocument.isPending}>
            {archiveDocument.isPending ? "Archiving..." : "Archive"}
          </button>
        )}
        <button type="button" className="danger" onClick={() => void handleDelete()} disabled={deleteDocument.isPending}>
          Delete
        </button>
        {!isEditing && (
          <button type="button" className="secondary" onClick={startEditing}>
            Edit metadata
          </button>
        )}
      </div>
      <p className="knowledge-hint">
        {document.source_type === "website"
          ? "Refresh refetches the page, creating a new version only if its content has changed."
          : "Refresh re-indexes this document from its stored text - useful after a chunking change. Upload the file again to replace its content."}
      </p>

      {isEditing && (
        <Card title="Edit metadata">
          <form className="knowledge-form" onSubmit={handleSaveMetadata}>
            <label>
              Title
              <input type="text" value={editTitle} onChange={(event) => setEditTitle(event.target.value)} required />
            </label>
            <label>
              Description
              <textarea
                value={editDescription}
                onChange={(event) => setEditDescription(event.target.value)}
                rows={3}
              />
            </label>
            <label>
              Category
              <select value={editCategory} onChange={(event) => setEditCategory(event.target.value)}>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {formatKnowledgeLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tags <span className="knowledge-optional">comma separated</span>
              <input type="text" value={editTags} onChange={(event) => setEditTags(event.target.value)} />
            </label>
            <label>
              Industries <span className="knowledge-optional">comma separated</span>
              <input type="text" value={editIndustries} onChange={(event) => setEditIndustries(event.target.value)} />
            </label>
            <label>
              Technologies <span className="knowledge-optional">comma separated</span>
              <input
                type="text"
                value={editTechnologies}
                onChange={(event) => setEditTechnologies(event.target.value)}
              />
            </label>
            <div className="knowledge-actions">
              <button type="submit" disabled={updateMetadata.isPending}>
                {updateMetadata.isPending ? "Saving..." : "Save"}
              </button>
              <button type="button" className="secondary" onClick={() => setIsEditing(false)}>
                Cancel
              </button>
            </div>
            <p className="knowledge-hint">
              Changing the category or tags re-indexes this document, so retrieval filters stay accurate.
            </p>
          </form>
        </Card>
      )}

      <Card title="Details">
        <dl className="knowledge-detail-grid">
          <div>
            <dt>Source</dt>
            <dd>{formatSourceType(document.source_type)}</dd>
          </div>
          <div>
            <dt>Reference</dt>
            <dd className="knowledge-detail-ref">
              {document.source_type === "website" ? (
                <a href={document.source_ref} target="_blank" rel="noreferrer noopener">
                  {document.source_ref}
                </a>
              ) : (
                document.source_ref
              )}
            </dd>
          </div>
          <div>
            <dt>File type</dt>
            <dd>{document.file_type ? document.file_type.toUpperCase() : "-"}</dd>
          </div>
          <div>
            <dt>Size</dt>
            <dd>{formatFileSize(document.file_size_bytes)}</dd>
          </div>
          <div>
            <dt>Searchable passages</dt>
            <dd>{document.chunk_count}</dd>
          </div>
          <div>
            <dt>Author</dt>
            <dd>{document.author ?? "-"}</dd>
          </div>
          <div>
            <dt>Added</dt>
            <dd>{formatTimestamp(document.created_at)}</dd>
          </div>
          <div>
            <dt>Last indexed</dt>
            <dd>{formatTimestamp(document.last_indexed_at)}</dd>
          </div>
          <div>
            <dt>Last refreshed</dt>
            <dd>{formatTimestamp(document.last_refreshed_at)}</dd>
          </div>
        </dl>

        {document.description && <p className="knowledge-detail-description">{document.description}</p>}

        {(document.tags?.length || document.industries?.length || document.technologies?.length) && (
          <div className="knowledge-tag-groups">
            {document.tags?.length ? (
              <div>
                <span className="knowledge-tag-label">Tags</span>
                {document.tags.map((tag) => (
                  <Badge key={tag} label={tag} />
                ))}
              </div>
            ) : null}
            {document.industries?.length ? (
              <div>
                <span className="knowledge-tag-label">Industries</span>
                {document.industries.map((item) => (
                  <Badge key={item} label={item} />
                ))}
              </div>
            ) : null}
            {document.technologies?.length ? (
              <div>
                <span className="knowledge-tag-label">Technologies</span>
                {document.technologies.map((item) => (
                  <Badge key={item} label={item} />
                ))}
              </div>
            ) : null}
          </div>
        )}
      </Card>

      <Card title="Content preview">
        {document.content_preview ? (
          <>
            <pre className="knowledge-preview">{document.content_preview}</pre>
            {document.content_truncated && (
              <p className="knowledge-hint">
                Showing the beginning of the extracted text. Scout searches the whole document.
              </p>
            )}
          </>
        ) : (
          <EmptyState message="No extracted text stored for this document." />
        )}
      </Card>

      <Card title="Version history">
        {versionsQuery.isLoading ? (
          <LoadingState />
        ) : versionsQuery.isError ? (
          <ErrorState message={getErrorMessage(versionsQuery.error)} />
        ) : versions.length <= 1 ? (
          <EmptyState message="This is the only version of this document." />
        ) : (
          <ul className="knowledge-version-list">
            {versions.map((version) => (
              <li
                key={version.id}
                className={`knowledge-version-item${version.id === document.id ? " current" : ""}`}
              >
                <span>Version {version.version}</span>
                <Badge label={formatKnowledgeLabel(version.status)} variant={knowledgeStatusVariant(version.status)} />
                <span>{formatTimestamp(version.created_at)}</span>
                {version.id === document.id ? (
                  <Badge label="Viewing" variant="success" />
                ) : (
                  <Link to={`/knowledge/${version.id}`}>Open</Link>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
