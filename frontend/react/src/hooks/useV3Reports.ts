import { useQuery } from "@tanstack/react-query";
import { v3ReportService } from "../services/v3ReportService";

export function useV3Reports(companyId: string | undefined) {
  return useQuery({
    queryKey: ["v3-reports", companyId],
    queryFn: () => v3ReportService.listForCompany(companyId as string),
    enabled: companyId !== undefined,
  });
}
