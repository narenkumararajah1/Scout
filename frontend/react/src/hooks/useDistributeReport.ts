import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reportService } from "../services/reportService";

export function useDistributeReport(reportId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => reportService.distributeReport(reportId as string),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["report-deliveries", reportId] });
    },
  });
}
