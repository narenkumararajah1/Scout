import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useCompanies } from "../hooks/useCompanies";
import { useNotifications } from "../hooks/useNotifications";
import { useOpportunityRankings } from "../hooks/useOpportunityRankings";
import { getErrorMessage } from "../utils/errors";

export function DashboardPage() {
  const companiesQuery = useCompanies();
  const notificationsQuery = useNotifications({ limit: 10 });
  const opportunitiesQuery = useOpportunityRankings(5);

  const companies = companiesQuery.data ?? [];
  const notifications = notificationsQuery.data ?? [];
  const topOpportunities = opportunitiesQuery.data ?? [];
  const monitoredCount = companies.filter((company) => company.monitoring_status === "enabled").length;
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  return (
    <div className="dashboard-page">
      <h1>Executive Dashboard</h1>

      <div className="dashboard-summary">
        <Card title="Companies monitored">
          {companiesQuery.isLoading ? (
            <LoadingState />
          ) : companiesQuery.isError ? (
            <ErrorState message={getErrorMessage(companiesQuery.error)} />
          ) : (
            <p className="stat">{companies.length}</p>
          )}
        </Card>
        <Card title="Actively monitored">
          {companiesQuery.isLoading ? (
            <LoadingState />
          ) : companiesQuery.isError ? (
            <ErrorState message={getErrorMessage(companiesQuery.error)} />
          ) : (
            <p className="stat">{monitoredCount}</p>
          )}
        </Card>
        <Card title="Unread notifications">
          {notificationsQuery.isLoading ? (
            <LoadingState />
          ) : notificationsQuery.isError ? (
            <ErrorState message={getErrorMessage(notificationsQuery.error)} />
          ) : (
            <p className="stat">{unreadCount}</p>
          )}
        </Card>
      </div>

      <Card title="Recent notifications">
        {notificationsQuery.isLoading ? (
          <LoadingState />
        ) : notificationsQuery.isError ? (
          <ErrorState message={getErrorMessage(notificationsQuery.error)} />
        ) : notifications.length === 0 ? (
          <EmptyState message="No notifications yet." />
        ) : (
          <ul className="notification-list">
            {notifications.map((notification) => (
              <li key={notification.id} className="notification-item">
                <div className="notification-item-header">
                  <span>{notification.title}</span>
                  {!notification.is_read && <Badge label="New" variant="success" />}
                </div>
                {notification.summary && <p className="notification-summary">{notification.summary}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Top Opportunities">
        {opportunitiesQuery.isLoading ? (
          <LoadingState />
        ) : opportunitiesQuery.isError ? (
          <ErrorState message={getErrorMessage(opportunitiesQuery.error)} />
        ) : topOpportunities.length === 0 ? (
          <EmptyState message="No opportunities yet." />
        ) : (
          <ul className="opportunity-list">
            {topOpportunities.map((opportunity) => (
              <li key={opportunity.id} className="opportunity-list-item">
                <div className="opportunity-list-item-header">
                  <span>{opportunity.title}</span>
                  {opportunity.priority !== null && <Badge label={`Priority ${opportunity.priority}`} />}
                </div>
                <Link to={`/companies/${opportunity.company_id}`}>View company</Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
