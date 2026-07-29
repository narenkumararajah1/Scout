// Presentation helpers shared by the Knowledge Library list and detail
// pages (V3 Enhancements Phase 1B). Follows utils/outreachDraft.ts's
// pattern of keeping a status-to-Badge mapping in one place so the two
// pages can never disagree about what "failed" looks like.
import type { BadgeVariant } from "../components/ui/Badge";
import type { KnowledgeDocumentStatus } from "../types/knowledgeDocument";

export function knowledgeStatusVariant(status: KnowledgeDocumentStatus | string): BadgeVariant {
  if (status === "ready") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "archived") {
    return "neutral";
  }
  // processing and requires_refresh both mean "not currently serving
  // Scout its best answer", which is the warning case.
  return "warning";
}

// The backend's vocabularies are snake_case identifiers
// ("case_studies", "requires_refresh"); these are for display only and
// are never sent back.
export function formatKnowledgeLabel(value: string): string {
  return value
    .split("_")
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(" ");
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  upload: "Uploaded file",
  website: "Website",
  local_directory: "Knowledge sources folder",
};

export function formatSourceType(sourceType: string): string {
  return SOURCE_TYPE_LABELS[sourceType] ?? formatKnowledgeLabel(sourceType);
}

const KILOBYTE = 1024;

export function formatFileSize(bytes: number | null): string {
  if (bytes === null || Number.isNaN(bytes)) {
    return "-";
  }
  if (bytes < KILOBYTE) {
    return `${bytes} B`;
  }
  if (bytes < KILOBYTE * KILOBYTE) {
    return `${(bytes / KILOBYTE).toFixed(1)} KB`;
  }
  return `${(bytes / (KILOBYTE * KILOBYTE)).toFixed(1)} MB`;
}

export function formatTimestamp(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

// Splits the comma-separated text the metadata forms use into the arrays
// the JSON endpoints expect.
export function parseCommaSeparated(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
