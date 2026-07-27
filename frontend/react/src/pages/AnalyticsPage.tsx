// Executive Intelligence Dashboard (roadmap Phase 3, item 3). Presents
// backend/services/analytics_service.py's executive_dashboard() exactly
// as returned - no new aggregation on the frontend, no charting library
// (stat cards/tables only), matching the existing Phase 7B convention.
// Replaces the old flat opportunity-rankings list: opportunities are now
// grouped by company, each with its confidence/priority explanation
// (already-persisted CapabilityMatch.reasoning + Signal type counts -
// zero new AI calls) and one-click Recommended Actions, reusing the
// same safe/rate-limited GenerationJob endpoints Scout Copilot's
// suggested actions already trigger (roadmap Phase 2).
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useExecutiveDashboard } from "../hooks/useExecutiveDashboard";
import { useToasts } from "../hooks/useToasts";
import { meetingBriefService } from "../services/meetingBriefService";
import { outreachDraftService } from "../services/outreachDraftService";
import { v3ReportService } from "../services/v3ReportService";
import type { ExecutiveDashboardOpportunity } from "../types/executiveDashboard";
import { getErrorMessage } from "../utils/errors";

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  hiring: "hiring signal",
  leadership: "leadership signal",
  strategic: "strategic signal",
  technology: "technology signal",
};

function signalTypeLabel(type: string, count: number): string {
  const base = SIGNAL_TYPE_LABELS[type] ?? `${type} signal`;
  return count === 1 ? `1 ${base}` : `${count} ${base}s`;
}

type ActionType = "meeting_brief" | "outreach_draft" | "report";

const ACTION_LABELS: Record<ActionType, string> = {
  meeting_brief: "Generate Meeting Brief",
  outreach_draft: "Generate Outreach Draft",
  report: "Generate Report",
};

export function AnalyticsPage() {
  const dashboardQuery = useExecutiveDashboard(50);
  const companies = dashboardQuery.data?.companies ?? [];
  const { toasts, pushToast, dismissToast } = useToasts();
  const [triggeringAction, setTriggeringAction] = useState<string | null>(null);

  async function handleAction(companyId: string, actionType: ActionType) {
    const actionKey = `${companyId}-${actionType}`;
    setTriggeringAction(actionKey);
    try {
      if (actionType === "meeting_brief") {
        await meetingBriefService.generate(companyId);
      } else if (actionType === "outreach_draft") {
        await outreachDraftService.generate({ companyId, outreachType: "Email", talkingPoints: [] });
      } else {
        await v3ReportService.generate(companyId);
      }
      pushToast(`${ACTION_LABELS[actionType]} started - open the company page to watch it finish.`, "success");
    } catch (error) {
      pushToast(getErrorMessage(error), "error");
    } finally {
      setTriggeringAction(null);
    }
  }

  function renderOpportunity(companyId: string, opportunity: ExecutiveDashboardOpportunity) {
    const signalEntries = Object.entries(opportunity.signal_type_counts);

    return (
      <li key={opportunity.id} className="opportunity-list-item">
        <div className="opportunity-list-item-header">
          <span>{opportunity.title}</span>
          {opportunity.priority !== null && <Badge label={`Priority ${opportunity.priority}`} />}
        </div>
        {opportunity.confidence_score !== null && (
          <p className="opportunity-confidence">Confidence: {(opportunity.confidence_score * 100).toFixed(0)}%</p>
        )}
        {signalEntries.length > 0 && (
          <div className="exec-dashboard-signal-badges">
            {signalEntries.map(([type, count]) => (
              <Badge key={type} label={signalTypeLabel(type, count)} variant="neutral" />
            ))}
          </div>
        )}
        {opportunity.reasoning.length > 0 && (
          <ul className="exec-dashboard-reasoning">
            {opportunity.reasoning.map((reason, index) => (
              <li key={index}>{reason}</li>
            ))}
          </ul>
        )}
        <div className="exec-dashboard-actions">
          {(Object.keys(ACTION_LABELS) as ActionType[]).map((actionType) => {
            const actionKey = `${companyId}-${actionType}`;
            return (
              <button
                key={actionType}
                type="button"
                onClick={() => handleAction(companyId, actionType)}
                disabled={triggeringAction === actionKey}
              >
                {triggeringAction === actionKey ? "Starting..." : ACTION_LABELS[actionType]}
              </button>
            );
          })}
        </div>
      </li>
    );
  }

  return (
    <div className="analytics-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <h1>Executive Intelligence Dashboard</h1>
      <p className="card-description">
        The highest-priority opportunities across every company, grouped by company, with why each one scored the
        way it did and one-click actions to move it forward.
      </p>

      {dashboardQuery.isLoading ? (
        <LoadingState />
      ) : dashboardQuery.isError ? (
        <ErrorState message={getErrorMessage(dashboardQuery.error)} />
      ) : companies.length === 0 ? (
        <EmptyState message="No opportunities yet." />
      ) : (
        companies.map((company) => (
          <Card
            key={company.company_id}
            title={<Link to={`/companies/${company.company_id}`}>{company.company_name}</Link>}
          >
            <ul className="opportunity-list">
              {company.opportunities.map((opportunity) => renderOpportunity(company.company_id, opportunity))}
            </ul>
          </Card>
        ))
      )}
    </div>
  );
}
