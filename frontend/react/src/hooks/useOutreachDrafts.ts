import { useQuery } from "@tanstack/react-query";
import { outreachDraftService } from "../services/outreachDraftService";

export function useOutreachDrafts(companyId: string | undefined) {
  return useQuery({
    queryKey: ["outreach-drafts", companyId],
    queryFn: () => outreachDraftService.listForCompany(companyId as string),
    enabled: companyId !== undefined,
  });
}
