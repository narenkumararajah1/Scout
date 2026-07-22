// Conversational intelligence ("Ask Scout") domain operations (V2->V3
// parity pass). Wraps V2's existing, unversioned POST /conversation/ask
// (backend/routers/conversation.py, Phase 11) unchanged - a read-only
// Q&A over already-persisted intelligence that never triggers new
// research. No conversation history is persisted server-side, matching
// V2's own behavior - the frontend keeps history in memory only.
import { apiRequest } from "../api/client";

interface ConversationResponse {
  answer: string;
}

export const conversationService = {
  async ask(question: string): Promise<string> {
    const response = await apiRequest<ConversationResponse>("/conversation/ask", {
      method: "POST",
      body: { question },
    });
    return response.answer;
  },
};
