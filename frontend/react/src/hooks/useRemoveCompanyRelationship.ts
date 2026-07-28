import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

export function useRemoveCompanyRelationship(companyId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (relationshipId: string) => companyService.removeRelationship(companyId as string, relationshipId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["company-relationships", companyId] });
    },
  });
}
