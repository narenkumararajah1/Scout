import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// Companies opened most recently (V3 Enhancements Phase 6). Reads visit
// rows the company page has been writing since the earlier roadmap's
// Phase 3 - nothing new is recorded to make this work.
export function useRecentCompanies(limit = 6) {
  return useQuery({
    queryKey: ["recent-companies", limit],
    queryFn: () => companyService.listRecentCompanies(limit),
  });
}
