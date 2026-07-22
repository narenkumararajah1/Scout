// Displays a Sales Playbook exactly as generated in Phase 6 - the
// structured artifact stays structured (each section its own card),
// never flattened into a single text blob. Read-only: no regeneration
// trigger exists on this page.
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useSalesPlaybook } from "../hooks/useSalesPlaybook";
import { getErrorMessage } from "../utils/errors";

export function SalesPlaybookDetailPage() {
  const { playbookId } = useParams<{ playbookId: string }>();
  const playbookQuery = useSalesPlaybook(playbookId);

  if (!playbookId) {
    return <ErrorState message="No sales playbook selected." />;
  }

  if (playbookQuery.isLoading) {
    return <LoadingState message="Loading sales playbook..." />;
  }

  if (playbookQuery.isError || !playbookQuery.data) {
    return (
      <ErrorState message={playbookQuery.error ? getErrorMessage(playbookQuery.error) : "Sales playbook not found."} />
    );
  }

  const playbook = playbookQuery.data;

  return (
    <div className="sales-playbook-detail-page">
      <div className="page-header">
        <h1>Sales Playbook</h1>
        {playbook.confidence_score !== null && (
          <Badge label={`Confidence: ${(playbook.confidence_score * 100).toFixed(0)}%`} />
        )}
      </div>

      <Card title="Strategy Summary">
        {playbook.strategy_summary ? (
          <p className="report-section-text">{playbook.strategy_summary}</p>
        ) : (
          <EmptyState message="Not available." />
        )}
      </Card>

      <Card title="Discovery Questions">
        {playbook.discovery_questions.length === 0 ? (
          <EmptyState message="No discovery questions." />
        ) : (
          <ul>
            {playbook.discovery_questions.map((question, index) => (
              <li key={index}>{question}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Talking Points">
        {playbook.talking_points.length === 0 ? (
          <EmptyState message="No talking points." />
        ) : (
          <ul>
            {playbook.talking_points.map((point, index) => (
              <li key={index}>{point}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Objection Handling">
        {playbook.objection_handling.length === 0 ? (
          <EmptyState message="No objection handling notes." />
        ) : (
          <ul>
            {playbook.objection_handling.map((item, index) => (
              <li key={index}>
                <strong>{item.objection}</strong> — {item.response}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Recommended Services">
        {playbook.recommended_services.length === 0 ? (
          <EmptyState message="No recommended services." />
        ) : (
          <ul>
            {playbook.recommended_services.map((service, index) => (
              <li key={index}>{service}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Next Steps">
        {playbook.next_steps.length === 0 ? (
          <EmptyState message="No next steps." />
        ) : (
          <ul>
            {playbook.next_steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Risks">
        {playbook.risks.length === 0 ? (
          <EmptyState message="No risks noted." />
        ) : (
          <ul>
            {playbook.risks.map((risk, index) => (
              <li key={index}>{risk}</li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
