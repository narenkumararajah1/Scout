// Notification domain operations (V3 Phase 7A). Wraps this phase's new
// GET /api/v1/notifications (backend/api/routers/notifications.py),
// backed by Phase 5's notification_repository plus this phase's
// list_all_notifications() addition.
import { apiRequestData } from "../api/client";
import type { Notification } from "../types/notification";

export interface ListNotificationsOptions {
  limit?: number;
  unreadOnly?: boolean;
}

export const notificationService = {
  async listNotifications(options: ListNotificationsOptions = {}): Promise<Notification[]> {
    const params = new URLSearchParams();
    if (options.limit !== undefined) {
      params.set("limit", String(options.limit));
    }
    if (options.unreadOnly) {
      params.set("unread_only", "true");
    }
    const query = params.toString();
    return apiRequestData<Notification[]>(`/api/v1/notifications${query ? `?${query}` : ""}`);
  },
};
