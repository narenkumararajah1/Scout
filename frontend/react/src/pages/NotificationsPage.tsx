// Full notifications list with mark-as-read (V3 Phase 7B). Groups by
// the Notification entity's existing `type` field
// (technology/hiring/leadership/strategic - reused from V2's Signal
// categories, backend/database/models/notification.py) rather than a
// priority/severity taxonomy the backend doesn't have; unread items
// stay visually distinct via the existing "New" badge pattern from the
// Phase 7A dashboard widget.
import { useState } from "react";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useMarkNotificationRead } from "../hooks/useMarkNotificationRead";
import { useNotifications } from "../hooks/useNotifications";
import { useToasts } from "../hooks/useToasts";
import { getErrorMessage } from "../utils/errors";

export function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const notificationsQuery = useNotifications({ limit: 50, unreadOnly });
  const markRead = useMarkNotificationRead();
  const { toasts, pushToast, dismissToast } = useToasts();

  const notifications = notificationsQuery.data ?? [];

  function handleMarkRead(notificationId: string) {
    markRead.mutate(notificationId, {
      onSuccess: () => pushToast("Notification marked as read.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  return (
    <div className="notifications-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className="page-header">
        <h1>Notifications</h1>
        <label className="unread-only-toggle">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(event) => setUnreadOnly(event.target.checked)}
          />
          Unread only
        </label>
      </div>

      <Card title="All notifications">
        {notificationsQuery.isLoading ? (
          <LoadingState />
        ) : notificationsQuery.isError ? (
          <ErrorState message={getErrorMessage(notificationsQuery.error)} />
        ) : notifications.length === 0 ? (
          <EmptyState message="No notifications." />
        ) : (
          <ul className="notification-list">
            {notifications.map((notification) => (
              <li
                key={notification.id}
                className={`notification-list-item${notification.is_read ? "" : " unread"}`}
              >
                <div className="notification-item-header">
                  <Badge label={notification.type} />
                  <span>{notification.title}</span>
                  {!notification.is_read && <Badge label="New" variant="success" />}
                </div>
                {notification.summary && <p className="notification-summary">{notification.summary}</p>}
                {notification.recommended_action && (
                  <p className="notification-action">Recommended: {notification.recommended_action}</p>
                )}
                {!notification.is_read && (
                  <button
                    type="button"
                    onClick={() => handleMarkRead(notification.id)}
                    disabled={markRead.isPending}
                  >
                    Mark as read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
