// Displays the richer V3 Report (Phase 6) - a pure, already-assembled
// aggregation over Company Intelligence, Technology Analysis,
// Executive Intelligence, Opportunity/Capability Analysis, Sales
// Playbooks, Meeting Briefs, and Outreach Drafts. This page never
// regenerates the report; it only renders backend/services/
// v3_report_service.py's persisted `content` and offers the existing
// PDF export (Phase 6) as a download - no other export/share/print
// capability is fabricated.
import { useState } from "react";
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useV3Report } from "../hooks/useV3Report";
import { useToasts } from "../hooks/useToasts";
import { v3ReportService } from "../services/v3ReportService";
import { getErrorMessage } from "../utils/errors";

export function V3ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const reportQuery = useV3Report(reportId);
  const { toasts, pushToast, dismissToast } = useToasts();
  const [isExporting, setIsExporting] = useState(false);

  if (!reportId) {
    return <ErrorState message="No report selected." />;
  }

  if (reportQuery.isLoading) {
    return <LoadingState message="Loading report..." />;
  }

  if (reportQuery.isError || !reportQuery.data) {
    return <ErrorState message={reportQuery.error ? getErrorMessage(reportQuery.error) : "Report not found."} />;
  }

  const report = reportQuery.data;
  const companyIntelligence = report.content?.company_intelligence ?? null;
  const technologies = report.content?.technology_landscape ?? [];
  const opportunities = report.content?.opportunity_analysis ?? [];
  const capabilityMatches = report.content?.capability_alignment ?? [];
  const executives = report.content?.executive_intelligence ?? [];
  const salesPlaybooks = report.content?.sales_playbooks ?? [];
  const meetingBriefs = report.content?.meeting_briefs ?? [];
  const outreachDrafts = report.content?.outreach_drafts ?? [];

  async function handleExport() {
    setIsExporting(true);
    try {
      await v3ReportService.downloadPdf(reportId as string);
      pushToast("PDF downloaded.", "success");
    } catch (error) {
      pushToast(getErrorMessage(error), "error");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="v3-report-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className="page-header">
        <h1>{report.title ?? "Report"}</h1>
        <Badge label={report.status} variant={report.status === "Generated" ? "success" : "neutral"} />
        <button type="button" onClick={handleExport} disabled={isExporting}>
          {isExporting ? "Exporting..." : "Export PDF"}
        </button>
      </div>

      <Card title="Executive Summary">
        {report.executive_summary ? (
          <p className="report-section-text">{report.executive_summary}</p>
        ) : (
          <EmptyState message="Not available." />
        )}
      </Card>

      <Card title="Company Intelligence">
        {!companyIntelligence ? (
          <EmptyState message="Not available." />
        ) : (
          <dl className="company-overview">
            <dt>Industry</dt>
            <dd>{companyIntelligence.industry ?? "Unknown"}</dd>
            <dt>Headquarters</dt>
            <dd>{companyIntelligence.headquarters ?? "Unknown"}</dd>
            <dt>Business Initiatives</dt>
            <dd>{companyIntelligence.business_initiatives.join(", ") || "None"}</dd>
          </dl>
        )}
      </Card>

      <Card title="Technology Landscape">
        {technologies.length === 0 ? (
          <EmptyState message="No technologies recorded." />
        ) : (
          <ul>
            {technologies.map((tech, index) => (
              <li key={index}>
                {tech.name}
                {tech.category ? ` — ${tech.category}` : ""}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Opportunity Analysis">
        {opportunities.length === 0 ? (
          <EmptyState message="No opportunities recorded." />
        ) : (
          <ul>
            {opportunities.map((opportunity, index) => (
              <li key={index}>{opportunity.title}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Capability Alignment">
        {capabilityMatches.length === 0 ? (
          <EmptyState message="No capability matches recorded." />
        ) : (
          <ul>
            {capabilityMatches.map((match, index) => (
              <li key={index}>{match.capability_name}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Executive Intelligence">
        {executives.length === 0 ? (
          <EmptyState message="No executives recorded." />
        ) : (
          <ul>
            {executives.map((executive, index) => (
              <li key={index}>
                {executive.name}
                {executive.title ? ` — ${executive.title}` : ""}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Sales Playbooks">
        {salesPlaybooks.length === 0 ? (
          <EmptyState message="No sales playbooks recorded." />
        ) : (
          <ul>
            {salesPlaybooks.map((playbook, index) => (
              <li key={index}>{playbook.strategy_summary ?? "(no summary)"}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Meeting Briefs">
        {meetingBriefs.length === 0 ? (
          <EmptyState message="No meeting briefs recorded." />
        ) : (
          <ul>
            {meetingBriefs.map((brief, index) => (
              <li key={index}>{brief.meeting_title ?? "(untitled meeting)"}</li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Outreach Drafts">
        {outreachDrafts.length === 0 ? (
          <EmptyState message="No outreach drafts recorded." />
        ) : (
          <ul>
            {outreachDrafts.map((draft, index) => (
              <li key={index}>
                {draft.type} <Badge label={draft.status} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
