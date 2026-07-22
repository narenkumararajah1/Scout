import { useMutation, useQueryClient } from "@tanstack/react-query";
import { v3ReportService } from "../services/v3ReportService";

export function useGenerateV3Report(companyId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (title?: string) => v3ReportService.generate(companyId as string, title),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["v3-reports", companyId] });
    },
  });
}
