import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// The company's intelligence history - one entry per analysis run, newest
// first (07_COMPANY_REFRESH_ENGINE.md's "Intelligence Timeline").
export function useCompanySnapshots(companyId: string | undefined, limit = 20) {
  return useQuery({
    queryKey: ["company-snapshots", companyId, limit],
    queryFn: () => companyService.listSnapshots(companyId as string, limit),
    enabled: Boolean(companyId),
  });
}
