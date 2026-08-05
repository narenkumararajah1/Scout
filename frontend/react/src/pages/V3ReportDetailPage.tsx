// Displays the richer V3 Report (Phase 6) - a pure, already-assembled
// aggregation over Company Intelligence, Technology Analysis,
// Executive Intelligence, Opportunity/Capability Analysis, Sales
// Playbooks, Meeting Briefs, and Outreach Drafts. This page never
// regenerates the report; it only renders backend/services/
// v3_report_service.py's persisted `content` and offers the existing
// PDF export (Phase 6) as a download, plus Distribute, which sends the
// report through the same delivery service the V2 report page uses.
import { useState } from "react";
import { useParams } from "react-router-dom";
import { Breadcrumbs } from "../components/ui/Breadcrumbs";
import { RelatedArtifacts } from "../components/ui/RelatedArtifacts";
import { AIFeedback } from "../components/ui/AIFeedback";
import { Badge } from "../components/ui/Badge";
import { CapabilityCard } from "../components/ui/CapabilityCard";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { CategoryBarChart } from "../components/charts/CategoryBarChart";
import { OpportunityScoreChart } from "../components/charts/OpportunityScoreChart";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { OpportunityCard } from "../components/ui/OpportunityCard";
import { ProseSection } from "../components/ui/ProseSection";
import { ToastContainer } from "../components/ui/Toast";
import { useConfirm } from "../hooks/useConfirm";
import { useDistributeIntelligenceReport } from "../hooks/useDistributeIntelligenceReport";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { useV3Report } from "../hooks/useV3Report";
import { useToasts } from "../hooks/useToasts";
import { v3ReportService } from "../services/v3ReportService";
import { countByCategory } from "../utils/opportunityCategory";
import { getErrorMessage } from "../utils/errors";

export function V3ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const reportQuery = useV3Report(reportId);
  const { toasts, pushToast, dismissToast } = useToasts();
  const [isExporting, setIsExporting] = useState(false);
  const { confirm, confirmDialog } = useConfirm();
  const statusQuery = useSystemStatus();
  const distributeReport = useDistributeIntelligenceReport(reportId);

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

  // Roadmap Phase 5 (Visual Intelligence) - both charts below are pure
  // client-side re-groupings of data already embedded in this same
  // report's content, computed fresh each render (no new fetch, no new
  // backend field). Technology Stack groups by the category Knowledge
  // Extraction already assigned each technology (verbatim, no
  // reclassification); Opportunity Distribution buckets each
  // opportunity's recommended services into the roadmap's own named
  // practice categories via countByCategory's keyword matching.
  const technologyCategoryCounts = new Map<string, number>();
  for (const tech of technologies) {
    const category = tech.category ?? "Uncategorized";
    technologyCategoryCounts.set(category, (technologyCategoryCounts.get(category) ?? 0) + 1);
  }
  const technologyStack = Array.from(technologyCategoryCounts.entries())
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count);
  const opportunityDistribution = countByCategory(opportunities.flatMap((o) => o.recommended_services));

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

  async function handleDistribute() {
    // Same production-safety wording as the V2 report page: say whether
    // this actually leaves the building before asking, not after.
    const delivery = statusQuery.data?.delivery;
    const isLive = delivery ? delivery.email_live || delivery.teams_live : true;
    if (
      !(await confirm(
        isLive
          ? "Send this report to every eligible recipient now? This sends real email/Teams messages and can't be undone."
          : "Send this report to every eligible recipient now? Delivery is currently in dry-run mode - no real message will be sent.",
      ))
    ) {
      return;
    }
    pushToast("Sending report...", "progress");
    distributeReport.mutate(undefined, {
      onSuccess: (deliveries) => {
        const sent = deliveries.filter((d) => d.status === "sent").length;
        pushToast(`Distributed to ${sent} of ${deliveries.length} delivery attempt(s).`, "success");
      },
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  return (
    <div className="v3-report-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <Breadcrumbs companyId={report.company_id} current="Intelligence Report" />
      <RelatedArtifacts companyId={report.company_id} current="report" />

      <div className="page-header">
        <h1>{report.title ?? "Report"}</h1>
        <Badge label={report.status} variant={report.status === "Generated" ? "success" : "neutral"} />
        <button type="button" onClick={handleExport} disabled={isExporting}>
          {isExporting ? "Exporting..." : "Export PDF"}
        </button>
        {/* Beside Export, matching the V2 report page: those are the two
            things you do with a finished report, and having Distribute on
            only one of them meant the same document was sendable from one
            screen and not the other. */}
        <button type="button" onClick={handleDistribute} disabled={distributeReport.isPending}>
          {distributeReport.isPending ? "Sending..." : "Distribute Report"}
        </button>
      </div>

      <Card title="Executive Summary">
        {report.executive_summary ? (
          <ProseSection text={report.executive_summary} lead />
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

      <Card title="Technology Stack">
        <CategoryBarChart data={technologyStack} emptyMessage="No technologies recorded." />
      </Card>

      <Card title="Opportunity Distribution">
        <CategoryBarChart data={opportunityDistribution} emptyMessage="No opportunities recorded." />
      </Card>

      <Card title="Opportunity Score & Confidence">
        <OpportunityScoreChart data={opportunities} />
      </Card>

      <Card title="Technology Landscape">
        {technologies.length === 0 ? (
          <EmptyState message="No technologies recorded." />
        ) : (
          <ul className="tag-item-list">
            {technologies.map((tech, index) => (
              <li key={index} className="tag-item">
                <span className="tag-item-name">{tech.name}</span>
                <span className="tag-item-badges">
                  {tech.category && <Badge label={tech.category} variant="neutral" />}
                  {tech.adoption_status && <Badge label={tech.adoption_status} variant="success" />}
                </span>
                {tech.business_relevance && <p className="tag-item-detail">{tech.business_relevance}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Opportunity Analysis">
        {opportunities.length === 0 ? (
          <EmptyState message="No opportunities recorded." />
        ) : (
          <div className="opportunity-grid">
            {opportunities.map((opportunity, index) => (
              <OpportunityCard
                key={index}
                title={opportunity.title}
                priority={opportunity.priority}
                confidence={opportunity.confidence_score}
                description={opportunity.description ?? ""}
                recommendedServices={opportunity.recommended_services}
              />
            ))}
          </div>
        )}
      </Card>

      <Card title="Capability Alignment">
        {capabilityMatches.length === 0 ? (
          <EmptyState message="No capability matches recorded." />
        ) : (
          <div className="capability-list">
            {capabilityMatches.map((match, index) => (
              <CapabilityCard
                key={index}
                name={match.capability_name}
                confidence={match.confidence}
                description={match.reasoning}
              />
            ))}
          </div>
        )}
      </Card>

      <Card title="Executive Intelligence">
        {executives.length === 0 ? (
          <EmptyState message="No executives recorded." />
        ) : (
          <ul className="tag-item-list">
            {executives.map((executive, index) => (
              <li key={index} className="tag-item">
                <span className="tag-item-name">
                  {executive.name}
                  {executive.title ? ` — ${executive.title}` : ""}
                </span>
                {executive.biography && <p className="tag-item-detail">{executive.biography}</p>}
                {executive.business_priorities && executive.business_priorities.length > 0 && (
                  <ul className="bullet-list bullet-list-compact">
                    {executive.business_priorities.map((priority, priorityIndex) => (
                      <li key={priorityIndex} className="bullet-list-item">
                        {priority}
                      </li>
                    ))}
                  </ul>
                )}
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

      <AIFeedback targetType="report" targetId={reportId as string} companyId={report.company_id} />
    </div>
  );
}
