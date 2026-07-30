// What Innominds knowledge grounded a generated artifact (V3 Enhancements
// Phase 3B). Mirrors backend/schemas/grounded_in.py.
//
// Shared by Sales Playbook, Meeting Brief and Outreach Draft rather than
// declared per artifact - all three attach the same shape from the same
// Evidence layer, and three copies would drift.

export interface GroundedInItem {
  id: string;
  // Readable typed label: "Case Study: Meridian Health Systems",
  // "Capability: Platform Engineering", "capability_match:...". This is what
  // makes the list scannable without expanding anything.
  source: string;
  content: string;
  url: string | null;
  confidence_score: number | null;
  retrieved_at: string | null;
}
