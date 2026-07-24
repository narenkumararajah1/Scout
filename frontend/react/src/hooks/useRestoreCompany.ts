import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useRestoreCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (companyId: string) => companyService.restoreCompany(companyId),
    onSuccess: (company) => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      void queryClient.invalidateQueries({ queryKey: ["company", company.id] });
    },
  });
}
