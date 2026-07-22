import { useQuery } from "@tanstack/react-query";
import { reportService } from "../services/reportService";

export function useReport(reportId: string | undefined) {
  return useQuery({
    queryKey: ["report", reportId],
    queryFn: () => reportService.getReport(reportId as string),
    enabled: reportId !== undefined,
  });
}
