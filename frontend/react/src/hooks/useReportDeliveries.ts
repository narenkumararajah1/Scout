import { useQuery } from "@tanstack/react-query";
import { reportService } from "../services/reportService";

export function useReportDeliveries(reportId: string | undefined) {
  return useQuery({
    queryKey: ["report-deliveries", reportId],
    queryFn: () => reportService.getReportDeliveries(reportId as string),
    enabled: reportId !== undefined,
  });
}
