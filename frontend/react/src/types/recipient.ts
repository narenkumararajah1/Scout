// Mirrors backend/models/recipient.py's Recipient.

export interface Recipient {
  id: string;
  name: string;
  email: string;
  delivery_status: string | null;
  preferred_frequency: string | null;
  preferred_company_ids: string[];
  preferred_channels: string[];
  created_at: string;
}

export interface CreateRecipientInput {
  name: string;
  email: string;
  preferred_frequency?: string;
  preferred_company_ids?: string[];
  preferred_channels?: string[];
}

export interface UpdateRecipientPreferencesInput {
  preferred_frequency?: string;
  preferred_company_ids?: string[];
  preferred_channels?: string[];
}
