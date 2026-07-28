import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";
import type { CreateCompanyRelationshipInput } from "../types/companyRelationship";

export function useAddCompanyRelationship(companyId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCompanyRelationshipInput) => companyService.addRelationship(companyId as string, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["company-relationships", companyId] });
    },
  });
}
