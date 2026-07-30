import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// The refresh summary from the company's most recent analysis run (V3
// Enhancements Phase 2B). Returns null for a company that has never been
// analysed - the page renders that as a prompt rather than an error.
export function useRefreshSummary(companyId: string | undefined) {
  return useQuery({
    queryKey: ["refresh-summary", companyId],
    queryFn: () => companyService.getRefreshSummary(companyId as string),
    enabled: Boolean(companyId),
  });
}
