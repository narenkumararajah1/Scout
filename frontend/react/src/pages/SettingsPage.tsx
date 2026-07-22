// Read-only account and system status information (V3 Phase 7C). No
// profile editing, preference management, integration management, or
// API key management - none of that exists in the backend, and this
// page does not fabricate any of it. Account info comes from the
// AuthContext's already-loaded GET /api/v1/auth/me result; system
// status comes from V2's existing GET /system/status.
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useWorkflowHistory } from "../hooks/useWorkflowHistory";
import { getErrorMessage } from "../utils/errors";

const WORKFLOW_STATUS_VARIANT: Record<string, BadgeVariant> = {
  completed: "success",
  failed: "danger",
};

export function SettingsPage() {
  const { user } = useAuth();
  const statusQuery = useSystemStatus();
  const workflowHistoryQuery = useWorkflowHistory();
  const recentRuns = (workflowHistoryQuery.data ?? []).slice(0, 10);

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <Card title="Account">
        {user ? (
          <dl className="company-overview">
            <dt>Email</dt>
            <dd>{user.email}</dd>
            <dt>Status</dt>
            <dd>
              <Badge label={user.is_active ? "Active" : "Inactive"} variant={user.is_active ? "success" : "neutral"} />
            </dd>
          </dl>
        ) : (
          <LoadingState message="Loading account..." />
        )}
      </Card>

      <Card title="System Status">
        {statusQuery.isLoading ? (
          <LoadingState />
        ) : statusQuery.isError ? (
          <ErrorState message={getErrorMessage(statusQuery.error)} />
        ) : statusQuery.data ? (
          <dl className="company-overview">
            <dt>Overall status</dt>
            <dd>
              <Badge
                label={statusQuery.data.health.status}
                variant={statusQuery.data.health.status === "ok" ? "success" : "warning"}
              />
            </dd>
            <dt>Database</dt>
            <dd>
              <Badge
                label={statusQuery.data.health.database_connected ? "Connected" : "Disconnected"}
                variant={statusQuery.data.health.database_connected ? "success" : "danger"}
              />
            </dd>
            <dt>Knowledge base (ChromaDB)</dt>
            <dd>
              <Badge
                label={statusQuery.data.health.chroma_connected ? "Connected" : "Disconnected"}
                variant={statusQuery.data.health.chroma_connected ? "success" : "danger"}
              />
            </dd>
            <dt>Scheduler</dt>
            <dd>
              <Badge
                label={statusQuery.data.scheduler.running ? "Running" : "Stopped"}
                variant={statusQuery.data.scheduler.running ? "success" : "neutral"}
              />
            </dd>
            <dt>Scheduler interval</dt>
            <dd>{statusQuery.data.scheduler.interval_hours} hour(s)</dd>
            <dt>Next scheduled run</dt>
            <dd>
              {statusQuery.data.scheduler.next_run_time
                ? new Date(statusQuery.data.scheduler.next_run_time).toLocaleString()
                : "Not scheduled"}
            </dd>
          </dl>
        ) : null}
      </Card>

      <Card title="Recent Workflow Runs">
        {workflowHistoryQuery.isLoading ? (
          <LoadingState />
        ) : workflowHistoryQuery.isError ? (
          <ErrorState message={getErrorMessage(workflowHistoryQuery.error)} />
        ) : recentRuns.length === 0 ? (
          <EmptyState message="No workflow runs yet." />
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Workflow ID</th>
                  <th>Status</th>
                  <th>Target Company</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.workflow_id}>
                    <td>{run.workflow_id.slice(0, 8)}</td>
                    <td>
                      <Badge label={run.status} variant={WORKFLOW_STATUS_VARIANT[run.status] ?? "neutral"} />
                    </td>
                    <td>{run.target_company ?? "N/A"}</td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
