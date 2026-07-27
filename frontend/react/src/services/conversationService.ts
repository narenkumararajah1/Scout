// Conversational intelligence ("Ask Scout" / Scout Copilot, roadmap
// Phase 2) - wraps V2's existing, unversioned POST /conversation/ask
// (backend/routers/conversation.py). Still never triggers new
// research; Phase 2 adds optional page context (companyId) and
// client-resent history (no server-side session store) so a
// conversation reads as continuous, plus related-company links and
// safe one-click generation-action suggestions in the response.
import { apiRequest } from "../api/client";
import type { AskScoutResult, ConversationTurn } from "../types/conversation";

export const conversationService = {
  async ask(question: string, companyId?: string, history: ConversationTurn[] = []): Promise<AskScoutResult> {
    return apiRequest<AskScoutResult>("/conversation/ask", {
      method: "POST",
      body: { question, company_id: companyId, history },
    });
  },
};
