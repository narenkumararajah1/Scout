import { useQuery } from "@tanstack/react-query";
import { reportService } from "../services/reportService";

export function useCompanyReports(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-reports", companyId],
    queryFn: () => reportService.listCompanyReports(companyId as string),
    enabled: companyId !== undefined,
  });
}
