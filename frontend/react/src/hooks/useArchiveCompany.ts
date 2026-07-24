import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// Priority 5 (soft delete/archive) - the primary "remove a company"
// action; unlike the old hard delete, every relationship stays intact.
export function useArchiveCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (companyId: string) => companyService.archiveCompany(companyId),
    onSuccess: (company) => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      void queryClient.invalidateQueries({ queryKey: ["company", company.id] });
    },
  });
}
