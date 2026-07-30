// Displays a Sales Playbook exactly as generated in Phase 6 - the
// structured artifact stays structured (each section its own card),
// never flattened into a single text blob. Read-only: no regeneration
// trigger exists on this page.
import { Link, useParams } from "react-router-dom";
import { AIFeedback } from "../components/ui/AIFeedback";
import { Badge } from "../components/ui/Badge";
import { BulletList } from "../components/ui/BulletList";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { GroundedInList } from "../components/ui/GroundedIn";
import { LoadingState } from "../components/ui/LoadingState";
import { ProseSection } from "../components/ui/ProseSection";
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
      <Link to={`/companies/${playbook.company_id}`} className="breadcrumb-back">
        ← Back to company
      </Link>

      <div className="page-header">
        <h1>Sales Playbook</h1>
        {playbook.confidence_score !== null && (
          <Badge label={`Confidence: ${(playbook.confidence_score * 100).toFixed(0)}%`} />
        )}
      </div>

      <Card title="Strategy Summary">
        {playbook.strategy_summary ? (
          <ProseSection text={playbook.strategy_summary} lead />
        ) : (
          <EmptyState message="Not available." />
        )}
      </Card>

      <Card title="Discovery Questions">
        {playbook.discovery_questions.length === 0 ? (
          <EmptyState message="No discovery questions." />
        ) : (
          <BulletList items={playbook.discovery_questions} />
        )}
      </Card>

      <Card title="Talking Points">
        {playbook.talking_points.length === 0 ? (
          <EmptyState message="No talking points." />
        ) : (
          <BulletList items={playbook.talking_points} />
        )}
      </Card>

      <Card title="Objection Handling">
        {playbook.objection_handling.length === 0 ? (
          <EmptyState message="No objection handling notes." />
        ) : (
          <div className="objection-list">
            {playbook.objection_handling.map((item, index) => (
              <div key={index} className="objection-item">
                <p className="objection-item-question">{item.objection}</p>
                <p className="objection-item-answer">{item.response}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Recommended Services">
        {playbook.recommended_services.length === 0 ? (
          <EmptyState message="No recommended services." />
        ) : (
          <BulletList items={playbook.recommended_services} />
        )}
      </Card>

      <Card title="Next Steps">
        {playbook.next_steps.length === 0 ? (
          <EmptyState message="No next steps." />
        ) : (
          <BulletList items={playbook.next_steps} />
        )}
      </Card>

      <Card title="Risks">
        {playbook.risks.length === 0 ? (
          <EmptyState message="No risks noted." />
        ) : (
          <BulletList items={playbook.risks} />
        )}
      </Card>

      {playbook.why_innominds && (
        <Card title="Why Innominds?">
          <ol className="why-innominds-map">
            <li>
              <span className="why-innominds-label">Customer Need</span>
              <p>{playbook.why_innominds.customer_need ?? "Not available."}</p>
            </li>
            <li>
              <span className="why-innominds-label">Relevant Innominds Practices</span>
              {playbook.why_innominds.relevant_practices.length === 0 ? (
                <EmptyState message="Not available." />
              ) : (
                <BulletList items={playbook.why_innominds.relevant_practices} />
              )}
            </li>
            <li>
              <span className="why-innominds-label">Relevant Experience</span>
              {/* grounded_in carries the same Evidence why_innominds
                  .relevant_experience is derived from, but with readable
                  labels ("Case Study: ...", "Capability: ..."). Rendering
                  the labelled form here rather than adding a separate
                  sources card avoids showing identical content twice on one
                  page; relevant_experience is the fallback for playbooks
                  generated before Phase 3B, whose responses predate the
                  labelled field (V3 Enhancements Phase 3B). */}
              {playbook.grounded_in && playbook.grounded_in.length > 0 ? (
                <GroundedInList items={playbook.grounded_in} />
              ) : playbook.why_innominds.relevant_experience.length === 0 ? (
                <EmptyState message="Not available." />
              ) : (
                <BulletList items={playbook.why_innominds.relevant_experience} />
              )}
            </li>
            <li>
              <span className="why-innominds-label">Suggested Sales Motion</span>
              {playbook.why_innominds.suggested_sales_motion.length === 0 ? (
                <EmptyState message="Not available." />
              ) : (
                <BulletList items={playbook.why_innominds.suggested_sales_motion} />
              )}
            </li>
          </ol>
        </Card>
      )}

      <AIFeedback targetType="sales_playbook" targetId={playbook.id} companyId={playbook.company_id} />
    </div>
  );
}
