import { useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationService } from "../services/notificationService";

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (notificationId: string) => notificationService.markNotificationRead(notificationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
