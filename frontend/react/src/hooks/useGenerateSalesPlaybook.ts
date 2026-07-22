import { useMutation, useQueryClient } from "@tanstack/react-query";
import { salesPlaybookService } from "../services/salesPlaybookService";

export function useGenerateSalesPlaybook(companyId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (opportunityId: string) => salesPlaybookService.generate(companyId as string, opportunityId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sales-playbooks", companyId] });
    },
  });
}
