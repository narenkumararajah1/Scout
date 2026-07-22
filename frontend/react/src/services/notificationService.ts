// Notification domain operations (V3 Phase 7A/7B). Wraps
// GET /api/v1/notifications (Phase 7A) and this phase's new
// POST /api/v1/notifications/{id}/read (backend/api/routers/notifications.py),
// both backed by Phase 5's notification_repository.
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

  async markNotificationRead(notificationId: string): Promise<Notification> {
    return apiRequestData<Notification>(`/api/v1/notifications/${notificationId}/read`, { method: "POST" });
  },
};
