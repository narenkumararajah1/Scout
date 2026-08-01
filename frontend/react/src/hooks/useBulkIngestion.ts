// Bulk ingestion for the Knowledge Library: many files, one at a time,
// through the ingestion pipeline that already exists.
//
// **Why the queue is here and not in the backend.** Ingesting N files is
// N calls to POST /api/v1/knowledge/documents/upload, which already does
// extraction, chunking, embedding, versioning, deduplication and
// metadata. A bulk endpoint would have to re-orchestrate all of that on
// the server and invent its own partial-failure reporting, duplicating
// the one thing worth not duplicating. Looping over the existing
// endpoint reuses it exactly, and gets per-file progress and
// continue-on-failure for free, because each file is already its own
// transaction.
//
// **Why sequential rather than parallel**, which is the obvious
// optimisation and the wrong one here:
//
//   - Deduplication is a read-then-write. Two identical files uploaded
//     concurrently can both miss the content-hash check and both insert,
//     which is precisely the duplicate the feature is meant to catch.
//   - Ingestion is embedding work. It now runs in a threadpool rather
//     than on the event loop, but that pool is finite; twenty concurrent
//     uploads would saturate it and stall every other request in the app.
//
// One at a time is slower and correct. A folder of a few hundred
// documents is a background chore, not an interaction anyone waits on.
import { useCallback, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { knowledgeService } from "../services/knowledgeService";

// Mirrors the backend's SUPPORTED_FILE_TYPES
// (backend/integrations/document_extraction.py). Filtering here means a
// folder's .DS_Store, images and spreadsheets are reported as skipped
// without a pointless round trip each - which matters, because picking a
// folder is how most of these batches will arrive.
const SUPPORTED_EXTENSIONS = ["pdf", "txt", "md", "html", "htm"];

// 409 Conflict is the backend's duplicate signal
// (knowledge_ingestion_service.DuplicateDocumentError). Matching on the
// status rather than the message keeps this from breaking the first time
// someone rewords the error.
const HTTP_CONFLICT = 409;

export type BulkFileStatus = "queued" | "ingesting" | "imported" | "duplicate" | "failed" | "skipped";

export interface BulkFileResult {
  /** Folder-relative path when available, so two same-named files are distinguishable. */
  path: string;
  name: string;
  sizeBytes: number;
  status: BulkFileStatus;
  /** Why it was skipped or how it failed; the duplicate's existing title. */
  detail?: string;
  chunkCount?: number;
  documentId?: string;
}

export interface BulkIngestionSummary {
  total: number;
  imported: number;
  duplicates: number;
  failed: number;
  skipped: number;
  chunksCreated: number;
  elapsedMs: number;
  cancelled: boolean;
}

export interface BulkIngestionInput {
  files: File[];
  category: string;
  tags?: string;
  industries?: string;
  technologies?: string;
  relatedServices?: string;
  author?: string;
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot + 1).toLowerCase();
}

function describe(file: File): { path: string; name: string } {
  // Set by the browser for folder (webkitdirectory) picks, absent for
  // multi-file picks.
  const relative = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
  return { path: relative && relative.length > 0 ? relative : file.name, name: file.name };
}

export function useBulkIngestion() {
  const [files, setFiles] = useState<BulkFileResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [summary, setSummary] = useState<BulkIngestionSummary | null>(null);
  const cancelRef = useRef(false);

  const reset = useCallback(() => {
    cancelRef.current = false;
    setFiles([]);
    setSummary(null);
  }, []);

  const cancel = useCallback(() => {
    // Stops before the next file rather than aborting the one in flight:
    // a half-ingested document is worse than one extra document.
    cancelRef.current = true;
  }, []);

  const start = useCallback(async (input: BulkIngestionInput) => {
    cancelRef.current = false;
    setSummary(null);
    setIsRunning(true);
    const startedAt = Date.now();

    const initial: BulkFileResult[] = input.files.map((file) => {
      const { path, name } = describe(file);
      const extension = extensionOf(name);
      const supported = SUPPORTED_EXTENSIONS.includes(extension);
      return {
        path,
        name,
        sizeBytes: file.size,
        status: supported ? "queued" : "skipped",
        detail: supported
          ? undefined
          : `${extension ? `.${extension}` : "No extension"} is not an ingestible type`,
      };
    });
    setFiles(initial);

    const update = (index: number, patch: Partial<BulkFileResult>) =>
      setFiles((current) => current.map((item, i) => (i === index ? { ...item, ...patch } : item)));

    for (let index = 0; index < input.files.length; index += 1) {
      if (cancelRef.current) break;
      if (initial[index].status === "skipped") continue;

      update(index, { status: "ingesting" });
      try {
        const document = await knowledgeService.uploadDocument({
          file: input.files[index],
          category: input.category,
          tags: input.tags,
          industries: input.industries,
          technologies: input.technologies,
          relatedServices: input.relatedServices,
          author: input.author,
        });
        initial[index] = {
          ...initial[index],
          status: "imported",
          chunkCount: document.chunk_count,
          documentId: document.id,
          // A document that indexed badly is still imported, but the
          // reason it holds no chunks is worth surfacing here rather
          // than only on its detail page.
          detail: document.status === "failed" ? (document.status_detail ?? "Indexing failed") : undefined,
        };
      } catch (error) {
        const isDuplicate = error instanceof ApiError && error.status === HTTP_CONFLICT;
        initial[index] = {
          ...initial[index],
          status: isDuplicate ? "duplicate" : "failed",
          detail: error instanceof Error ? error.message : "Ingestion failed",
        };
      }
      update(index, initial[index]);
    }

    const counted = (status: BulkFileStatus) => initial.filter((f) => f.status === status).length;
    setSummary({
      total: initial.length,
      imported: counted("imported"),
      duplicates: counted("duplicate"),
      failed: counted("failed"),
      skipped: counted("skipped"),
      chunksCreated: initial.reduce((sum, f) => sum + (f.chunkCount ?? 0), 0),
      elapsedMs: Date.now() - startedAt,
      // Anything still queued means the run stopped early, which the
      // summary has to say or the counts look like a completed batch
      // that silently lost files.
      cancelled: cancelRef.current || initial.some((f) => f.status === "queued"),
    });
    setIsRunning(false);
  }, []);

  const processed = files.filter((f) => f.status !== "queued" && f.status !== "ingesting").length;

  return { files, isRunning, summary, processed, total: files.length, start, cancel, reset };
}
