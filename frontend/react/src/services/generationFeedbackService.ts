// AI feedback (Priority 4) - persist-only, no retraining or scoring.
import { apiRequestData } from "../api/client";
import type { GenerationFeedback, SubmitGenerationFeedbackRequest } from "../types/generationFeedback";

export const generationFeedbackService = {
  async submit(request: SubmitGenerationFeedbackRequest): Promise<GenerationFeedback> {
    return apiRequestData<GenerationFeedback>("/api/v1/feedback", { method: "POST", body: request });
  },
};
