// Polls a generation job until it reaches a terminal state (Priority
// 1). Every generation flow (Sales Playbook, Meeting Brief, Outreach
// Draft, Report) shares this one hook instead of each inventing its
// own polling loop.
import { useQuery } from "@tanstack/react-query";
import { generationJobService } from "../services/generationJobService";

const POLL_INTERVAL_MS = 1500;

export function useGenerationJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ["generation-job", jobId],
    queryFn: () => generationJobService.get(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : POLL_INTERVAL_MS;
    },
  });
}
