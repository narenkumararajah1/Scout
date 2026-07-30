// Executive Briefing (roadmap Phase 4, item 11 - "a five-minute
// briefing before every customer interaction"). Displays a Meeting
// Brief exactly as generated, reusing Company Intelligence, Executive
// Intelligence, and Engagement Strategy's output as already persisted -
// this page never regenerates analysis, only displays it. Section
// order/naming follows the roadmap's Executive Briefing contents
// exactly: Company Snapshot, Executive Summary, Recent Developments,
// Risks, Opportunities, Talking Points, Discovery Questions,
// Recommended Actions.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AIFeedback } from "../components/ui/AIFeedback";
import { Badge } from "../components/ui/Badge";
import { BulletList } from "../components/ui/BulletList";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { GroundedIn } from "../components/ui/GroundedIn";
import { LoadingState } from "../components/ui/LoadingState";
import { ProseSection } from "../components/ui/ProseSection";
import { ToastContainer } from "../components/ui/Toast";
import { useCompany } from "../hooks/useCompany";
import { useMeetingBrief } from "../hooks/useMeetingBrief";
import { useToasts } from "../hooks/useToasts";
import { outreachDraftService } from "../services/outreachDraftService";
import { v3ReportService } from "../services/v3ReportService";
import { getErrorMessage } from "../utils/errors";

export function MeetingBriefDetailPage() {
  const { briefId } = useParams<{ briefId: string }>();
  const briefQuery = useMeetingBrief(briefId);
  const companyQuery = useCompany(briefQuery.data?.company_id);
  const { toasts, pushToast, dismissToast } = useToasts();
  const [triggeringAction, setTriggeringAction] = useState<string | null>(null);

  async function handleAction(companyId: string, actionType: "outreach_draft" | "report") {
    setTriggeringAction(actionType);
    try {
      if (actionType === "outreach_draft") {
        await outreachDraftService.generate({ companyId, outreachType: "Email", talkingPoints: [] });
      } else {
        await v3ReportService.generate(companyId);
      }
      pushToast("Started - open the company page to watch it finish.", "success");
    } catch (error) {
      pushToast(getErrorMessage(error), "error");
    } finally {
      setTriggeringAction(null);
    }
  }

  if (!briefId) {
    return <ErrorState message="No meeting brief selected." />;
  }

  if (briefQuery.isLoading) {
    return <LoadingState message="Loading briefing..." />;
  }

  if (briefQuery.isError || !briefQuery.data) {
    return <ErrorState message={briefQuery.error ? getErrorMessage(briefQuery.error) : "Meeting brief not found."} />;
  }

  const brief = briefQuery.data;
  const company = companyQuery.data;

  return (
    <div className="meeting-brief-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <Link to={`/companies/${brief.company_id}`} className="breadcrumb-back">
        ← Back to company
      </Link>

      <div className="page-header">
        <h1>{brief.meeting_title ?? "Executive Briefing"}</h1>
        {brief.confidence_score !== null && (
          <Badge label={`Confidence: ${(brief.confidence_score * 100).toFixed(0)}%`} />
        )}
      </div>

      <Card title="Company Snapshot">
        {company ? (
          <dl className="company-overview">
            <dt>Industry</dt>
            <dd>{company.industry ?? "Unknown"}</dd>
            <dt>Headquarters</dt>
            <dd>{company.headquarters ?? "Unknown"}</dd>
            <dt>Website</dt>
            <dd>{company.website ?? "Unknown"}</dd>
          </dl>
        ) : (
          <LoadingState message="Loading company..." />
        )}
      </Card>

      <Card title="Executive Summary">
        {brief.executive_summary ? (
          <ProseSection text={brief.executive_summary} lead />
        ) : (
          <EmptyState message="Not available." />
        )}
        {brief.business_priorities.length > 0 && <BulletList items={brief.business_priorities} />}
      </Card>

      <Card title="Recent Developments">
        {brief.recent_developments.length === 0 ? (
          <EmptyState message="No recent developments detected." />
        ) : (
          <BulletList items={brief.recent_developments} />
        )}
      </Card>

      <Card title="Risks">
        {brief.risks.length === 0 ? (
          <EmptyState message="No risks identified." />
        ) : (
          <BulletList items={brief.risks} />
        )}
      </Card>

      <Card title="Opportunities">
        {brief.related_opportunities.length === 0 ? (
          <EmptyState message="No opportunities yet." />
        ) : (
          <BulletList items={brief.related_opportunities} />
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

      <Card title="Recommended Actions">
        {brief.recommended_services.length > 0 && <BulletList items={brief.recommended_services} />}
        <div className="exec-dashboard-actions">
          <button
            type="button"
            onClick={() => handleAction(brief.company_id, "outreach_draft")}
            disabled={triggeringAction === "outreach_draft"}
          >
            {triggeringAction === "outreach_draft" ? "Starting..." : "Generate Outreach Draft"}
          </button>
          <button
            type="button"
            onClick={() => handleAction(brief.company_id, "report")}
            disabled={triggeringAction === "report"}
          >
            {triggeringAction === "report" ? "Starting..." : "Generate Report"}
          </button>
          <Link to={`/companies/${brief.company_id}`}>View Company</Link>
        </div>
      </Card>

      {/* Placed just before the feedback control on purpose: a reviewer
          deciding whether this brief is any good is exactly who wants to
          see what it was built from (V3 Enhancements Phase 3B). */}
      <GroundedIn items={brief.grounded_in} />

      <AIFeedback targetType="meeting_brief" targetId={brief.id} companyId={brief.company_id} />
    </div>
  );
}
