import type { BadgeVariant } from "../components/ui/Badge";

// Shared across every place an Outreach Draft's status renders as a
// Badge (Company Details, Sales Enablement, the detail page) so the
// "Sent" status (outreach workflow redesign) only needed adding once.
export function outreachStatusVariant(status: string): BadgeVariant {
  if (status === "Approved" || status === "Sent") {
    return "success";
  }
  if (status === "Archived") {
    return "neutral";
  }
  return "warning";
}
