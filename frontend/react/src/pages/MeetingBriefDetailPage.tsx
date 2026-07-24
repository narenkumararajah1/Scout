// Displays a Meeting Brief exactly as generated in Phase 6, reusing
// Company Intelligence, Executive Intelligence, and Engagement
// Strategy's output as already persisted - this page never regenerates
// analysis, only displays it.
import { Link, useParams } from "react-router-dom";
import { AIFeedback } from "../components/ui/AIFeedback";
import { Badge } from "../components/ui/Badge";
import { BulletList } from "../components/ui/BulletList";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ProseSection } from "../components/ui/ProseSection";
import { useMeetingBrief } from "../hooks/useMeetingBrief";
import { getErrorMessage } from "../utils/errors";

export function MeetingBriefDetailPage() {
  const { briefId } = useParams<{ briefId: string }>();
  const briefQuery = useMeetingBrief(briefId);

  if (!briefId) {
    return <ErrorState message="No meeting brief selected." />;
  }

  if (briefQuery.isLoading) {
    return <LoadingState message="Loading meeting brief..." />;
  }

  if (briefQuery.isError || !briefQuery.data) {
    return <ErrorState message={briefQuery.error ? getErrorMessage(briefQuery.error) : "Meeting brief not found."} />;
  }

  const brief = briefQuery.data;

  return (
    <div className="meeting-brief-detail-page">
      <Link to={`/companies/${brief.company_id}`} className="breadcrumb-back">
        ← Back to company
      </Link>

      <div className="page-header">
        <h1>{brief.meeting_title ?? "Meeting Brief"}</h1>
        {brief.confidence_score !== null && (
          <Badge label={`Confidence: ${(brief.confidence_score * 100).toFixed(0)}%`} />
        )}
      </div>

      <Card title="Executive Summary">
        {brief.executive_summary ? (
          <ProseSection text={brief.executive_summary} lead />
        ) : (
          <EmptyState message="Not available." />
        )}
      </Card>

      <Card title="Business Priorities">
        {brief.business_priorities.length === 0 ? (
          <EmptyState message="No business priorities." />
        ) : (
          <BulletList items={brief.business_priorities} />
        )}
      </Card>

      <Card title="Executive Profiles">
        {brief.executive_profiles.length === 0 ? (
          <EmptyState message="No executive profiles." />
        ) : (
          <ul>
            {brief.executive_profiles.map((executive, index) => (
              <li key={index}>
                {executive.name}
                {executive.title ? ` — ${executive.title}` : ""}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Meeting Objectives">
        {brief.meeting_objectives.length === 0 ? (
          <EmptyState message="No meeting objectives." />
        ) : (
          <BulletList items={brief.meeting_objectives} />
        )}
      </Card>

      <Card title="Talking Points">
        {brief.talking_points.length === 0 ? (
          <EmptyState message="No talking points." />
        ) : (
          <BulletList items={brief.talking_points} />
        )}
      </Card>

      <Card title="Discovery Questions">
        {brief.discovery_questions.length === 0 ? (
          <EmptyState message="No discovery questions." />
        ) : (
          <BulletList items={brief.discovery_questions} />
        )}
      </Card>

      <Card title="Recommended Services">
        {brief.recommended_services.length === 0 ? (
          <EmptyState message="No recommended services." />
        ) : (
          <BulletList items={brief.recommended_services} />
        )}
      </Card>

      <AIFeedback targetType="meeting_brief" targetId={brief.id} companyId={brief.company_id} />
    </div>
  );
}
