import { useQuery } from "@tanstack/react-query";
import { salesPlaybookService } from "../services/salesPlaybookService";

export function useSalesPlaybooks(companyId: string | undefined) {
  return useQuery({
    queryKey: ["sales-playbooks", companyId],
    queryFn: () => salesPlaybookService.listForCompany(companyId as string),
    enabled: companyId !== undefined,
  });
}
