import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// A company's technology stack with the observation evidence behind each
// entry. Already ordered by the backend (most-observed first), so the UI
// never re-sorts and cannot disagree with the API about what leads.
export function useCompanyTechnologies(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-technologies", companyId],
    queryFn: () => companyService.listTechnologies(companyId as string),
    enabled: Boolean(companyId),
  });
}
