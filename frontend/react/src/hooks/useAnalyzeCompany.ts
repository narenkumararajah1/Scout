import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// Wraps the existing, already-live POST /companies/{id}/analyze
// (V2 Phase 9's full Research -> Capability Matching -> Opportunity
// Analysis -> Reporting pipeline). This hook adds no new behavior to
// that pipeline - only cache invalidation so the Company Details page
// reflects the freshly generated report and updated trends.
export function useAnalyzeCompany(companyId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => companyService.analyzeCompany(companyId as string),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["company-reports", companyId] });
      void queryClient.invalidateQueries({ queryKey: ["company-trends", companyId] });
    },
  });
}
