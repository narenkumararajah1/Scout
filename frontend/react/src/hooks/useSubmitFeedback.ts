// AI feedback (Priority 4). One mutation hook backs the AIFeedback
// control wherever it's dropped in (Sales Playbook, Meeting Brief,
// Outreach Draft, Report detail pages).
import { useMutation } from "@tanstack/react-query";
import { generationFeedbackService } from "../services/generationFeedbackService";

export function useSubmitFeedback() {
  return useMutation({ mutationFn: generationFeedbackService.submit });
}
