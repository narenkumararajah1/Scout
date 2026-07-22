import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useCompany(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company", companyId],
    queryFn: () => companyService.getCompany(companyId as string),
    enabled: companyId !== undefined,
  });
}
