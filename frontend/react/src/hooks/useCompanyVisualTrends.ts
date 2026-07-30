import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// The company's intelligence history, shaped for visualisation (V3
// Enhancements Phase 5). A company that has never been analysed returns
// an empty payload rather than an error, so charts render their own
// empty states instead of a failure.
export function useCompanyVisualTrends(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-visual-trends", companyId],
    queryFn: () => companyService.getVisualTrends(companyId as string),
    enabled: Boolean(companyId),
  });
}
