import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useRemoveCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (companyId: string) => companyService.removeCompany(companyId),
    onSuccess: (_data, companyId) => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      void queryClient.invalidateQueries({ queryKey: ["company", companyId] });
    },
  });
}
