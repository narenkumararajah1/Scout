import { useMutation, useQueryClient } from "@tanstack/react-query";
import { recipientService } from "../services/recipientService";
import type { CreateRecipientInput, UpdateRecipientPreferencesInput } from "../types/recipient";

export function useRecipientActions() {
  const queryClient = useQueryClient();

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["recipients"] });
  }

  const createRecipient = useMutation({
    mutationFn: (input: CreateRecipientInput) => recipientService.createRecipient(input),
    onSuccess: invalidate,
  });

  const updatePreferences = useMutation({
    mutationFn: ({ recipientId, input }: { recipientId: string; input: UpdateRecipientPreferencesInput }) =>
      recipientService.updateRecipientPreferences(recipientId, input),
    onSuccess: invalidate,
  });

  const enableRecipient = useMutation({
    mutationFn: (recipientId: string) => recipientService.enableRecipient(recipientId),
    onSuccess: invalidate,
  });

  const disableRecipient = useMutation({
    mutationFn: (recipientId: string) => recipientService.disableRecipient(recipientId),
    onSuccess: invalidate,
  });

  const removeRecipient = useMutation({
    mutationFn: (recipientId: string) => recipientService.removeRecipient(recipientId),
    onSuccess: invalidate,
  });

  return { createRecipient, updatePreferences, enableRecipient, disableRecipient, removeRecipient };
}
