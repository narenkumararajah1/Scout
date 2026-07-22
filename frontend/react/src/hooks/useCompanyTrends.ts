import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "../services/analyticsService";

export function useCompanyTrends(companyId: string | undefined) {
  return useQuery({
    queryKey: ["company-trends", companyId],
    queryFn: () => analyticsService.companyTrends(companyId as string),
    enabled: companyId !== undefined,
  });
}
