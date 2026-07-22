// Presents backend/services/analytics_service.py's opportunity_rankings()
// exactly as returned - no new aggregation on the frontend, and no
// charting library (stat cards/tables only), per the approved Phase 7B
// plan. Company-scoped trends live on the Company Details page instead
// of here, since that endpoint needs a company already in context.
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useOpportunityRankings } from "../hooks/useOpportunityRankings";
import { getErrorMessage } from "../utils/errors";

export function AnalyticsPage() {
  const rankingsQuery = useOpportunityRankings(20);
  const opportunities = rankingsQuery.data ?? [];

  return (
    <div className="analytics-page">
      <h1>Analytics</h1>

      <Card title="Opportunity Rankings">
        {rankingsQuery.isLoading ? (
          <LoadingState />
        ) : rankingsQuery.isError ? (
          <ErrorState message={getErrorMessage(rankingsQuery.error)} />
        ) : opportunities.length === 0 ? (
          <EmptyState message="No opportunities yet." />
        ) : (
          <ul className="opportunity-list">
            {opportunities.map((opportunity) => (
              <li key={opportunity.id} className="opportunity-list-item">
                <div className="opportunity-list-item-header">
                  <span>{opportunity.title}</span>
                  {opportunity.priority !== null && <Badge label={`Priority ${opportunity.priority}`} />}
                </div>
                {opportunity.description && <p className="opportunity-description">{opportunity.description}</p>}
                {opportunity.confidence_score !== null && (
                  <p className="opportunity-confidence">
                    Confidence: {(opportunity.confidence_score * 100).toFixed(0)}%
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
