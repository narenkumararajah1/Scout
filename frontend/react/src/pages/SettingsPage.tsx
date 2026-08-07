// Settings - is Scout healthy, and what has it actually run?
//
// This page used to carry four cards, two of which now belong to
// Administration: delivery safety and scheduler configuration are things
// you administer, not things you look up here. Repeating them would mean
// two pages disagreeing the moment one of them changed, so they are gone
// and a pointer takes their place.
//
// What is genuinely left is small and mostly boolean, so the page stays
// restrained by design rather than by omission:
//
//   account  - the only personal thing in the product, read-only because
//              no profile-editing endpoint exists.
//   health   - the three dependencies Scout degrades without: Postgres,
//              the vector store, and retrieval on top of it.
//   runs     - what the workflow has actually executed. The old table led
//              with a truncated workflow UUID, which links nowhere (there
//              is no run detail route) and told the reader nothing; the
//              company, the stages reached and any errors are what matter.
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useWorkflowHistory } from "../hooks/useWorkflowHistory";
import { getErrorMessage } from "../utils/errors";

const RUN_LIMIT = 10;

export function SettingsPage() {
  const { user } = useAuth();
  const statusQuery = useSystemStatus();
  const workflowQuery = useWorkflowHistory();

  const status = statusQuery.data;
  const runs = (workflowQuery.data ?? []).slice(0, RUN_LIMIT);

  const dependencies = status
    ? [
        { label: "Database", ok: status.health.database_connected },
        { label: "Vector store", ok: status.health.chroma_connected },
        { label: "Knowledge retrieval", ok: status.health.knowledge_retrieval },
      ]
    : [];
  const unhealthy = dependencies.filter((dependency) => !dependency.ok);

  return (
    <div className="settings">
      <header className="settings-head">
        <h1>Settings</h1>
        <p className="ops-hint">Your account, and whether Scout is working.</p>
      </header>

      {/* --- account ------------------------------------------------------ */}
      <section className="ops-panel" aria-label="Account">
        <div className="ops-panel-head">
          <div>
            <h2>Account</h2>
          </div>
        </div>

        {user ? (
          <dl className="ops-facts">
            <div className="ops-fact">
              <dt>Email</dt>
              <dd className="ops-fact-text">{user.email}</dd>
            </div>
            <div className="ops-fact">
              <dt>Status</dt>
              <dd>
                <Badge
                  label={user.is_active ? "Active" : "Inactive"}
                  variant={user.is_active ? "success" : "neutral"}
                />
              </dd>
            </div>
          </dl>
        ) : (
          <LoadingState message="Loading account..." />
        )}
      </section>

      {/* --- health ------------------------------------------------------- */}
      <section className="ops-panel" aria-label="System health">
        <div className="ops-panel-head">
          <div>
            <h2>System health</h2>
            <p className="ops-hint">
              {unhealthy.length === 0
                ? "The services Scout depends on to research, remember and answer."
                : `${unhealthy.map((dependency) => dependency.label).join(" and ")} unreachable — Scout's answers will be incomplete until this is restored.`}
            </p>
          </div>
          <Link to="/administration" className="ops-link-button">
            Automation settings
          </Link>
        </div>

        {statusQuery.isLoading ? (
          <LoadingState />
        ) : statusQuery.isError ? (
          <ErrorState message={getErrorMessage(statusQuery.error)} onRetry={() => void statusQuery.refetch()} />
        ) : status ? (
          <ul className="health-list">
            {dependencies.map((dependency) => (
              <li key={dependency.label} className={`health-item${dependency.ok ? "" : " down"}`}>
                <span className="health-dot" aria-hidden="true" />
                <span className="health-label">{dependency.label}</span>
                <span className="health-state">{dependency.ok ? "Connected" : "Unreachable"}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      {/* --- runs --------------------------------------------------------- */}
      <section className="ops-panel" aria-label="Workflow runs">
        <div className="ops-panel-head">
          <div>
            <h2>Workflow runs</h2>
            <p className="ops-hint">What Scout's research workflow has executed, most recent first.</p>
          </div>
        </div>

        {workflowQuery.isLoading ? (
          <LoadingState />
        ) : workflowQuery.isError ? (
          <ErrorState message={getErrorMessage(workflowQuery.error)} onRetry={() => void workflowQuery.refetch()} />
        ) : runs.length === 0 ? (
          <EmptyState message="No workflow runs recorded yet." />
        ) : (
          <ul className="run-list">
            {runs.map((run) => {
              const stages = run.completed_stages?.length ?? 0;
              const errors = run.errors?.length ?? 0;
              return (
                <li key={run.workflow_id} className={`run-item${errors > 0 ? " has-errors" : ""}`}>
                  <div className="run-main">
                    <span className="run-target">{run.target_company ?? "No target recorded"}</span>
                    <Badge
                      label={run.status}
                      variant={run.status === "completed" ? "success" : run.status === "failed" ? "danger" : "neutral"}
                    />
                  </div>
                  <div className="run-meta">
                    <span>
                      {stages} stage{stages === 1 ? "" : "s"} completed
                    </span>
                    {run.current_stage && <span>reached {run.current_stage}</span>}
                    {errors > 0 && <span className="run-errors">{errors} error{errors === 1 ? "" : "s"}</span>}
                    <span className="run-when">{new Date(run.created_at).toLocaleString()}</span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
