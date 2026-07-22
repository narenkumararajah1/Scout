// Recipient domain operations (V2->V3 parity pass). Wraps V2's
// existing, unversioned /recipients/* endpoints
// (backend/routers/recipients.py, Phase 9) exactly as they are -
// no new backend work, per "reuse existing backend functionality
// whenever possible."
import { apiRequest } from "../api/client";
import type { CreateRecipientInput, Recipient, UpdateRecipientPreferencesInput } from "../types/recipient";

export const recipientService = {
  async listRecipients(): Promise<Recipient[]> {
    return apiRequest<Recipient[]>("/recipients");
  },

  async createRecipient(input: CreateRecipientInput): Promise<Recipient> {
    return apiRequest<Recipient>("/recipients", { method: "POST", body: input });
  },

  async updateRecipientPreferences(
    recipientId: string,
    input: UpdateRecipientPreferencesInput,
  ): Promise<Recipient> {
    return apiRequest<Recipient>(`/recipients/${recipientId}`, { method: "PATCH", body: input });
  },

  async enableRecipient(recipientId: string): Promise<Recipient> {
    return apiRequest<Recipient>(`/recipients/${recipientId}/enable`, { method: "POST" });
  },

  async disableRecipient(recipientId: string): Promise<Recipient> {
    return apiRequest<Recipient>(`/recipients/${recipientId}/disable`, { method: "POST" });
  },

  async removeRecipient(recipientId: string): Promise<void> {
    await apiRequest<void>(`/recipients/${recipientId}`, { method: "DELETE" });
  },
};
