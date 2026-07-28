import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useCompanyRelationships(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-relationships", companyId],
    queryFn: () => companyService.listRelationships(companyId as string),
    enabled: companyId !== undefined,
  });
}
