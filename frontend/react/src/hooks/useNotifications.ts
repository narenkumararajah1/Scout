import { useQuery } from "@tanstack/react-query";
import { notificationService, type ListNotificationsOptions } from "../services/notificationService";

export function useNotifications(options: ListNotificationsOptions = {}) {
  return useQuery({
    queryKey: ["notifications", options],
    queryFn: () => notificationService.listNotifications(options),
  });
}
