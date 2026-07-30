import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// The people Scout knows at a company, with the org map and ranked paths
// in (V3 Enhancements Phase 4B). A company that has never been analysed
// returns an empty overview rather than an error, so the card renders a
// prompt instead of a failure.
export function useCompanyExecutives(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-executives", companyId],
    queryFn: () => companyService.getExecutives(companyId as string),
    enabled: Boolean(companyId),
  });
}
