import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useRemoveCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (companyId: string) => companyService.removeCompany(companyId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });
}
