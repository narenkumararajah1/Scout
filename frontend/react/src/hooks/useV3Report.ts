import { useQuery } from "@tanstack/react-query";
import { v3ReportService } from "../services/v3ReportService";

export function useV3Report(reportId: string | undefined) {
  return useQuery({
    queryKey: ["v3-report", reportId],
    queryFn: () => v3ReportService.get(reportId as string),
    enabled: reportId !== undefined,
  });
}
