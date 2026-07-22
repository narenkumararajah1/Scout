import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useCompanyIntelligence(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-intelligence", companyId],
    queryFn: () => companyService.getCompanyIntelligence(companyId as string),
    enabled: companyId !== undefined,
  });
}
