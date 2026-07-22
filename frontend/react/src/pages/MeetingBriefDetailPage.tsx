// Displays a Meeting Brief exactly as generated in Phase 6, reusing
// Company Intelligence, Executive Intelligence, and Engagement
// Strategy's output as already persisted - this page never regenerates
// analysis, only displays it.
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
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
      <div className="page-header">
        <h1>{brief.meeting_title ?? "Meeting Brief"}</h1>
        {brief.confidence_score !== null && (
          <Badge label={`Confidence: ${(brief.confidence_score * 100).toFixed(0)}%`} />
        )}
      </div>

      <Card title="Executive Summary">
        {brief.executive_summary ? (
          <p className="report-section-text">{brief.executive_summary}</p>
        ) : (
          <EmptyState message="Not available." />
        )}
      </Card>

      <Card title="Business Priorities">
        {brief.business_priorities.length === 0 ? (
          <EmptyState message="No business priorities." />
        ) : (
          <ul>
            {brief.business_priorities.map((priority, index) => (
              <li key={index}>{priority}</li>
            ))}
          </ul>
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
          <ul>
            {brief.meeting_objectives.map((objective, index) => (
              <li key={index}>{objective}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Talking Points">
        {brief.talking_points.length === 0 ? (
          <EmptyState message="No talking points." />
        ) : (
          <ul>
            {brief.talking_points.map((point, index) => (
              <li key={index}>{point}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Discovery Questions">
        {brief.discovery_questions.length === 0 ? (
          <EmptyState message="No discovery questions." />
        ) : (
          <ul>
            {brief.discovery_questions.map((question, index) => (
              <li key={index}>{question}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Recommended Services">
        {brief.recommended_services.length === 0 ? (
          <EmptyState message="No recommended services." />
        ) : (
          <ul>
            {brief.recommended_services.map((service, index) => (
              <li key={index}>{service}</li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
