// Generic generation job status (Priority 1). Every generation
// service's generate() now returns a GenerationJob rather than the
// finished artifact; useGenerationJob polls this endpoint until the
// job is completed or failed.
import { apiRequestData } from "../api/client";
import type { GenerationJob } from "../types/generationJob";

export const generationJobService = {
  async get(jobId: string): Promise<GenerationJob> {
    return apiRequestData<GenerationJob>(`/api/v1/jobs/${jobId}`);
  },
};
