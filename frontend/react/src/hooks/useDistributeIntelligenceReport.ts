import { useMutation } from "@tanstack/react-query";
import { v3ReportService } from "../services/v3ReportService";

// The intelligence-report counterpart to useDistributeReport (which
// covers V2 reports). Same delivery service underneath - only the report
// shape differs, and the backend adapts it - so the two hooks stay
// separate purely because they address different endpoints.
//
// No cache invalidation: unlike V2 reports there is no deliveries list
// rendered on this page, and the mutation result carries the full
// outcome the caller reports.
export function useDistributeIntelligenceReport(reportId: string | undefined) {
  return useMutation({
    mutationFn: () => v3ReportService.distributeIntelligenceReport(reportId as string),
  });
}
