import { useMutation } from "@tanstack/react-query";
import { salesPlaybookService } from "../services/salesPlaybookService";

// Priority 1: returns a GenerationJob, not the finished playbook - the
// caller polls it with useGenerationJob and invalidates the
// ["sales-playbooks", companyId] list once that job completes.
export function useGenerateSalesPlaybook(companyId: string | undefined) {
  return useMutation({
    mutationFn: (opportunityId: string) => salesPlaybookService.generate(companyId as string, opportunityId),
  });
}
