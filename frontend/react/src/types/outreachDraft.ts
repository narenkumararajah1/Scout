// Mirrors backend/schemas/outreach_draft.py's OutreachDraftOut exactly.
// `status` is always "Draft" at creation; "Approved"/"Archived" only
// via the two dedicated approve/archive actions - Scout never sends
// anything regardless of status.

export interface OutreachDraft {
  id: string;
  company_id: string;
  opportunity_id: string | null;
  type: string;
  subject: string | null;
  content: string;
  status: string;
  created_at: string;
}
