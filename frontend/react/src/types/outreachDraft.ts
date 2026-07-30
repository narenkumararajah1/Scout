// Mirrors backend/schemas/outreach_draft.py's OutreachDraftOut exactly.
// `status` is always "Draft" at creation; "Approved"/"Archived" via the
// two human-reviewer actions, "Sent" only via a real send through
// POST /{id}/send (outreach workflow redesign - generation itself never
// changes status).

import type { GroundedInItem } from "./groundedIn";

export interface OutreachDraft {
  id: string;
  company_id: string;
  opportunity_id: string | null;
  type: string;
  subject: string | null;
  content: string;
  status: string;
  created_at: string;
  // Only present on the detail response, not in list results (V3
  // Enhancements Phase 3B).
  grounded_in?: GroundedInItem[];
}
