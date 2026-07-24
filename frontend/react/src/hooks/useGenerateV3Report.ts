import { useMutation } from "@tanstack/react-query";
import { v3ReportService } from "../services/v3ReportService";

// Priority 1: returns a GenerationJob, not the finished report - the
// caller polls it with useGenerationJob and invalidates the
// ["v3-reports", companyId] list once that job completes.
export function useGenerateV3Report(companyId: string | undefined) {
  return useMutation({
    mutationFn: (title?: string) => v3ReportService.generate(companyId as string, title),
  });
}
