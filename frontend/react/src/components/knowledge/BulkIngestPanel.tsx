// Bulk ingestion: pick many files (or a whole folder) and queue them
// through the same ingestion the single upload uses.
//
// **What this shows, and what it deliberately does not.** A folder of
// four hundred documents produces four hundred rows, and 394 of them say
// "imported", which is the one thing nobody needs to read. So while a
// run is in progress this shows counts and the file currently being
// worked on, and when it finishes it shows the summary plus *only the
// files that need a human*: what failed, what was already there, what was
// not an ingestible type. The successes are a number.
import { useMemo, useRef, useState } from "react";
import { useBulkIngestion, type BulkFileResult } from "../../hooks/useBulkIngestion";
import { formatFileSize, formatKnowledgeLabel } from "../../utils/knowledgeDocument";
import { Card } from "../ui/Card";

interface BulkIngestPanelProps {
  categories: string[];
  /** Lets the page refresh the catalog once a run finishes. */
  onComplete: () => void;
}

function FileGroup({ title, tone, files }: { title: string; tone: string; files: BulkFileResult[] }) {
  if (files.length === 0) return null;
  return (
    <details className="bulk-group" open={tone === "failed"}>
      <summary>
        <span className={`bulk-dot bulk-dot-${tone}`} aria-hidden="true" />
        {title} ({files.length})
      </summary>
      <ul className="bulk-group-list">
        {files.map((file) => (
          <li key={file.path}>
            <span className="bulk-file-path" title={file.path}>
              {file.path}
            </span>
            {file.detail && <span className="bulk-file-detail">{file.detail}</span>}
          </li>
        ))}
      </ul>
    </details>
  );
}

export function BulkIngestPanel({ categories, onComplete }: BulkIngestPanelProps) {
  const [selected, setSelected] = useState<File[]>([]);
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState("");
  const [industries, setIndustries] = useState("");
  const filesInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const { files, isRunning, summary, processed, total, start, cancel, reset } = useBulkIngestion();

  const selectedBytes = useMemo(() => selected.reduce((sum, f) => sum + f.size, 0), [selected]);
  const current = files.find((f) => f.status === "ingesting");
  const liveCounts = useMemo(
    () => ({
      imported: files.filter((f) => f.status === "imported").length,
      duplicate: files.filter((f) => f.status === "duplicate").length,
      failed: files.filter((f) => f.status === "failed").length,
      skipped: files.filter((f) => f.status === "skipped").length,
    }),
    [files],
  );

  function choose(list: FileList | null) {
    reset();
    setSelected(list ? Array.from(list) : []);
  }

  async function handleStart() {
    if (selected.length === 0 || !category) return;
    await start({ files: selected, category, tags, industries });
    onComplete();
  }

  function handleClear() {
    reset();
    setSelected([]);
    if (filesInputRef.current) filesInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
  }

  return (
    <Card title="Bulk import">
      <div className="knowledge-form bulk-panel">
        <div className="bulk-pickers">
          <label className="bulk-picker">
            Files
            <input
              ref={filesInputRef}
              type="file"
              multiple
              accept=".pdf,.txt,.md,.markdown,.html,.htm"
              onChange={(event) => choose(event.target.files)}
              disabled={isRunning}
            />
          </label>
          <label className="bulk-picker">
            Folder
            <input
              ref={folderInputRef}
              type="file"
              multiple
              // Not in React's typings, and not in every browser - Firefox
              // and Safari support it, but a browser without it simply
              // renders a normal multi-file picker rather than breaking.
              {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
              onChange={(event) => choose(event.target.files)}
              disabled={isRunning}
            />
          </label>
        </div>

        {selected.length > 0 && !summary && (
          <p className="bulk-selection">
            {selected.length} file{selected.length === 1 ? "" : "s"} selected · {formatFileSize(selectedBytes)}
          </p>
        )}

        <label>
          Category
          <select value={category} onChange={(event) => setCategory(event.target.value)} disabled={isRunning} required>
            <option value="">Select a category</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {formatKnowledgeLabel(item)}
              </option>
            ))}
          </select>
        </label>
        <p className="knowledge-hint">Applied to every document in the batch.</p>

        <label>
          Tags <span className="knowledge-optional">comma separated</span>
          <input type="text" value={tags} onChange={(e) => setTags(e.target.value)} disabled={isRunning} />
        </label>
        <label>
          Industries <span className="knowledge-optional">comma separated</span>
          <input type="text" value={industries} onChange={(e) => setIndustries(e.target.value)} disabled={isRunning} />
        </label>

        <div className="bulk-actions">
          <button type="button" onClick={handleStart} disabled={isRunning || selected.length === 0 || !category}>
            {isRunning ? "Importing..." : `Import ${selected.length || ""} document${selected.length === 1 ? "" : "s"}`}
          </button>
          {isRunning ? (
            <button type="button" className="bulk-secondary" onClick={cancel}>
              Stop after this file
            </button>
          ) : (
            (selected.length > 0 || summary) && (
              <button type="button" className="bulk-secondary" onClick={handleClear}>
                Clear
              </button>
            )
          )}
        </div>

        {isRunning && (
          <div className="bulk-progress" role="status" aria-live="polite">
            <div className="bulk-progress-bar">
              <div
                className="bulk-progress-fill"
                style={{ width: `${total ? Math.round((processed / total) * 100) : 0}%` }}
              />
            </div>
            <p className="bulk-progress-text">
              {processed} of {total} processed
              {current && <> · ingesting {current.name}</>}
            </p>
            <p className="bulk-progress-counts">
              {liveCounts.imported} imported · {liveCounts.duplicate} already present · {liveCounts.failed} failed ·{" "}
              {liveCounts.skipped} skipped
            </p>
          </div>
        )}

        {summary && (
          <div className="bulk-summary">
            <h4>
              {summary.cancelled ? "Import stopped" : "Import complete"}
              <span className="bulk-elapsed">{Math.round(summary.elapsedMs / 1000)}s</span>
            </h4>
            <dl className="bulk-summary-grid">
              <div>
                <dt>Imported</dt>
                <dd>{summary.imported}</dd>
              </div>
              <div>
                <dt>Already present</dt>
                <dd>{summary.duplicates}</dd>
              </div>
              <div>
                <dt>Failed</dt>
                <dd>{summary.failed}</dd>
              </div>
              <div>
                <dt>Skipped</dt>
                <dd>{summary.skipped}</dd>
              </div>
              <div>
                <dt>Passages indexed</dt>
                <dd>{summary.chunksCreated}</dd>
              </div>
            </dl>
            {summary.cancelled && (
              <p className="bulk-hint-warn">
                Stopped before the whole batch was processed. Re-running it will skip everything already imported.
              </p>
            )}

            <FileGroup title="Failed" tone="failed" files={files.filter((f) => f.status === "failed")} />
            <FileGroup title="Already in the Library" tone="duplicate" files={files.filter((f) => f.status === "duplicate")} />
            <FileGroup title="Skipped" tone="skipped" files={files.filter((f) => f.status === "skipped")} />
          </div>
        )}

        <p className="knowledge-hint">
          PDF, text, Markdown or HTML. Documents are ingested one at a time so a failure never stops the batch, and
          anything already in the Library is recognised and left alone.
        </p>
      </div>
    </Card>
  );
}
