// Mirrors backend/models/recipient.py's Delivery - read-only here.
// Distribution (creating new deliveries) is intentionally not exposed
// in this phase's frontend; see TECH_DEBT.md.

export interface Delivery {
  id: string;
  recipient_id: string;
  report_id: string;
  channel: string;
  delivery_time: string;
  status: string;
}
