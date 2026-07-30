// Presentation helpers for the Company Refresh Engine (V3 Enhancements
// Phase 2B). Follows utils/outreachDraft.ts's pattern of keeping the
// status-to-Badge mapping in one place.
import type { BadgeVariant } from "../components/ui/Badge";
import type { ChangeSignificance, ChangeType, DetectedChange } from "../types/refreshSummary";

// What kind of movement a change describes, in the user's words rather
// than the backend's enum. "resolved" is deliberately phrased as no
// longer *reported* rather than no longer true: research coverage varies
// between runs, so absence is weaker evidence than presence and the copy
// should not overclaim.
const CHANGE_TYPE_LABELS: Record<ChangeType, string> = {
  appeared: "New",
  resolved: "No longer reported",
  strengthened: "Strengthened",
  weakened: "Weakened",
  updated: "Restated",
};

export function changeTypeLabel(changeType: ChangeType | string): string {
  return CHANGE_TYPE_LABELS[changeType as ChangeType] ?? changeType;
}

export function changeTypeVariant(
  changeType: ChangeType | string,
  significance: ChangeSignificance | string,
): BadgeVariant {
  if (changeType === "strengthened" || (changeType === "appeared" && significance === "major")) {
    return "success";
  }
  if (changeType === "weakened") {
    return "warning";
  }
  return "neutral";
}

const CATEGORY_LABELS: Record<string, string> = {
  leadership: "Leadership",
  hiring: "Hiring",
  technology: "Technology",
  strategic: "Strategic",
  opportunity: "Opportunity",
  capability: "Capability",
  profile: "Profile",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function majorChanges(changes: DetectedChange[]): DetectedChange[] {
  return changes.filter((change) => change.significance === "major");
}

export function minorChanges(changes: DetectedChange[]): DetectedChange[] {
  return changes.filter((change) => change.significance !== "major");
}
