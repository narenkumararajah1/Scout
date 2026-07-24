import { useQuery } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useCompanies(includeArchived = false) {
  return useQuery({
    queryKey: ["companies", { includeArchived }],
    queryFn: () => companyService.listCompanies(includeArchived),
  });
}
