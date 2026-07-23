import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useAnalyzeCompany } from "../hooks/useAnalyzeCompany";
import { useCompany } from "../hooks/useCompany";
import { useConfirm } from "../hooks/useConfirm";
import { useCompanyIntelligence } from "../hooks/useCompanyIntelligence";
import { useCompanyReports } from "../hooks/useCompanyReports";
import { useCompanyTrends } from "../hooks/useCompanyTrends";
import { useGenerateMeetingBrief } from "../hooks/useGenerateMeetingBrief";
import { useGenerateOutreachDraft } from "../hooks/useGenerateOutreachDraft";
import { useGenerateSalesPlaybook } from "../hooks/useGenerateSalesPlaybook";
import { useGenerateV3Report } from "../hooks/useGenerateV3Report";
import { useMeetingBriefs } from "../hooks/useMeetingBriefs";
import { useOutreachDrafts } from "../hooks/useOutreachDrafts";
import { useRemoveCompany } from "../hooks/useRemoveCompany";
import { useSalesPlaybooks } from "../hooks/useSalesPlaybooks";
import { useToasts } from "../hooks/useToasts";
import { useV3Reports } from "../hooks/useV3Reports";
import { companyService } from "../services/companyService";
import { getErrorMessage } from "../utils/errors";
import { outreachStatusVariant } from "../utils/outreachDraft";

const OUTREACH_TYPES = ["Email", "Follow-up", "Meeting Request", "LinkedIn Message"];

export function CompanyDetailsPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const companyQuery = useCompany(companyId);
  const intelligenceQuery = useCompanyIntelligence(companyId);
  const reportsQuery = useCompanyReports(companyId);
  const trendsQuery = useCompanyTrends(companyId);
  const salesPlaybooksQuery = useSalesPlaybooks(companyId);
  const meetingBriefsQuery = useMeetingBriefs(companyId);
  const outreachDraftsQuery = useOutreachDrafts(companyId);
  const v3ReportsQuery = useV3Reports(companyId);
  const queryClient = useQueryClient();
  const { toasts, pushToast, dismissToast } = useToasts();
  const { confirm, confirmDialog } = useConfirm();

  const toggleMonitoring = useMutation({
    mutationFn: () => {
      const company = companyQuery.data;
      if (!company) {
        throw new Error("Company not loaded yet.");
      }
      return company.monitoring_status === "enabled"
        ? companyService.disableMonitoring(company.id)
        : companyService.enableMonitoring(company.id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["company", companyId] });
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  const analyzeCompany = useAnalyzeCompany(companyId);
  const removeCompany = useRemoveCompany();
  const generatePlaybook = useGenerateSalesPlaybook(companyId);
  const generateBrief = useGenerateMeetingBrief(companyId);
  const generateDraft = useGenerateOutreachDraft(companyId);
  const generateReport = useGenerateV3Report(companyId);

  const [selectedOpportunityId, setSelectedOpportunityId] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [reportTitle, setReportTitle] = useState("");
  const [outreachType, setOutreachType] = useState(OUTREACH_TYPES[0]);
  const [executiveName, setExecutiveName] = useState("");
  const [talkingPointsText, setTalkingPointsText] = useState("");
  const [outreachOpportunityId, setOutreachOpportunityId] = useState("");
  const [outreachMeetingBriefId, setOutreachMeetingBriefId] = useState("");

  function handleRunAnalysis() {
    pushToast("Analysis started - this can take a minute.", "progress");
    analyzeCompany.mutate(undefined, {
      onSuccess: () => pushToast("Analysis complete - a new report is ready.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGeneratePlaybook() {
    if (!selectedOpportunityId) {
      pushToast("Choose an opportunity first.", "error");
      return;
    }
    pushToast("Generating sales playbook...", "progress");
    generatePlaybook.mutate(selectedOpportunityId, {
      onSuccess: () => pushToast("Sales playbook generated.", "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGenerateBrief() {
    pushToast("Generating meeting brief...", "progress");
    generateBrief.mutate(meetingTitle || undefined, {
      onSuccess: () => {
        pushToast("Meeting brief generated.", "success");
        setMeetingTitle("");
      },
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGenerateReport() {
    pushToast("Assembling report...", "progress");
    generateReport.mutate(reportTitle || undefined, {
      onSuccess: () => {
        pushToast("Report generated.", "success");
        setReportTitle("");
      },
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGenerateDraft() {
    // Outreach workflow redesign: generation never requires an
    // executive - if one isn't chosen, the backend drafts a
    // high-quality generic outreach instead of blocking.
    const talkingPoints = talkingPointsText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    pushToast("Generating outreach draft...", "progress");
    generateDraft.mutate(
      {
        outreachType,
        executiveName: executiveName || undefined,
        talkingPoints,
        opportunityId: outreachOpportunityId || undefined,
        meetingBriefId: outreachMeetingBriefId || undefined,
      },
      {
        onSuccess: () => {
          pushToast("Outreach draft generated.", "success");
          setTalkingPointsText("");
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  async function handleRemove() {
    const company = companyQuery.data;
    if (!company) {
      return;
    }
    if (!(await confirm(`Remove ${company.name}? This can't be undone.`))) {
      return;
    }
    removeCompany.mutate(company.id, {
      onSuccess: () => navigate("/companies"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  if (!companyId) {
    return <ErrorState message="No company selected." />;
  }

  if (companyQuery.isLoading) {
    return <LoadingState message="Loading company..." />;
  }

  if (companyQuery.isError || !companyQuery.data) {
    return <ErrorState message={companyQuery.error ? getErrorMessage(companyQuery.error) : "Company not found."} />;
  }

  const company = companyQuery.data;
  const intelligence = intelligenceQuery.data;

  const trends = trendsQuery.data;

  return (
    <div className="company-details-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <Link to="/companies" className="breadcrumb-back">
        ← Companies
      </Link>

      <div className="page-header">
        <h1>{company.name}</h1>
        <Badge
          label={company.monitoring_status}
          variant={company.monitoring_status === "enabled" ? "success" : "neutral"}
        />
        <button type="button" onClick={() => toggleMonitoring.mutate()} disabled={toggleMonitoring.isPending}>
          {company.monitoring_status === "enabled" ? "Disable monitoring" : "Enable monitoring"}
        </button>
        <button
          type="button"
          className="company-remove-button"
          onClick={handleRemove}
          disabled={removeCompany.isPending}
        >
          Remove company
        </button>
        <button type="button" onClick={handleRunAnalysis} disabled={analyzeCompany.isPending}>
          {analyzeCompany.isPending ? "Running analysis..." : "Run Analysis"}
        </button>
      </div>

      {toggleMonitoring.isError && <p className="form-error">{getErrorMessage(toggleMonitoring.error)}</p>}

      <Card title="Overview">
        <dl className="company-overview">
          <dt>Industry</dt>
          <dd>{company.industry ?? "Unknown"}</dd>
          <dt>Headquarters</dt>
          <dd>{company.headquarters ?? "Unknown"}</dd>
          <dt>Website</dt>
          <dd>{company.website ?? "Unknown"}</dd>
        </dl>
      </Card>

      <Card title="Company Intelligence">
        {intelligenceQuery.isLoading ? (
          <LoadingState message="Loading intelligence..." />
        ) : intelligenceQuery.isError ? (
          <ErrorState message={getErrorMessage(intelligenceQuery.error)} />
        ) : !intelligence ? (
          <EmptyState message="No intelligence available yet." />
        ) : (
          <div className="intelligence-sections">
            <section>
              <h3>Technologies</h3>
              {intelligence.technologies.length === 0 ? (
                <EmptyState message="No technologies detected yet." />
              ) : (
                <ul>
                  {intelligence.technologies.map((tech) => (
                    <li key={tech.id}>
                      {tech.name}
                      {tech.category ? ` - ${tech.category}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Business Initiatives</h3>
              {intelligence.business_initiatives.length === 0 ? (
                <EmptyState message="No business initiatives detected yet." />
              ) : (
                <ul>
                  {intelligence.business_initiatives.map((initiative) => (
                    <li key={initiative.id}>{initiative.name}</li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Executives</h3>
              {intelligence.executives.length === 0 ? (
                <EmptyState message="No executives identified yet." />
              ) : (
                <ul>
                  {intelligence.executives.map((executive) => (
                    <li key={executive.id}>
                      {executive.name}
                      {executive.title ? ` - ${executive.title}` : ""}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Recent Signals</h3>
              {intelligence.recent_signals.length === 0 ? (
                <EmptyState message="No recent signals." />
              ) : (
                <ul>
                  {intelligence.recent_signals.map((signal) => (
                    <li key={signal.id}>{signal.title}</li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h3>Glean Knowledge</h3>
              {intelligence.glean_knowledge.length === 0 ? (
                <EmptyState message="No Glean results (Glean may not be configured)." />
              ) : (
                <ul>
                  {intelligence.glean_knowledge.map((item) => (
                    <li key={`${item.source}-${item.content}`}>{item.content}</li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </Card>

      <Card title="Trends">
        {trendsQuery.isLoading ? (
          <LoadingState message="Loading trends..." />
        ) : trendsQuery.isError ? (
          <ErrorState message={getErrorMessage(trendsQuery.error)} />
        ) : !trends ? (
          <EmptyState message="No trend data available yet." />
        ) : (
          <dl className="company-overview">
            <dt>Research sessions</dt>
            <dd>{trends.research_session_count}</dd>
            <dt>Opportunities</dt>
            <dd>{trends.opportunity_count}</dd>
            <dt>Reports</dt>
            <dd>{trends.report_count}</dd>
            <dt>Average opportunity confidence</dt>
            <dd>
              {trends.average_opportunity_confidence !== null
                ? `${(trends.average_opportunity_confidence * 100).toFixed(0)}%`
                : "Unknown"}
            </dd>
          </dl>
        )}
      </Card>

      <Card title="Reports">
        {reportsQuery.isLoading ? (
          <LoadingState message="Loading reports..." />
        ) : reportsQuery.isError ? (
          <ErrorState message={getErrorMessage(reportsQuery.error)} />
        ) : (reportsQuery.data ?? []).length === 0 ? (
          <EmptyState message="No reports yet - run an analysis to generate one." />
        ) : (
          <ul className="report-list">
            {(reportsQuery.data ?? []).map((report) => (
              <li key={report.id}>
                <Link to={`/reports/${report.id}`} className="report-list-item">
                  <span>Report</span>
                  <span>{new Date(report.created_at).toLocaleString()}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Sales Playbooks">
        <div className="generate-form">
          <select value={selectedOpportunityId} onChange={(event) => setSelectedOpportunityId(event.target.value)}>
            <option value="">Choose an opportunity...</option>
            {(trends?.top_opportunities ?? []).map((opportunity) => (
              <option key={opportunity.id} value={opportunity.id}>
                {opportunity.title}
              </option>
            ))}
          </select>
          <button type="button" onClick={handleGeneratePlaybook} disabled={generatePlaybook.isPending}>
            {generatePlaybook.isPending ? "Generating..." : "Generate Sales Playbook"}
          </button>
        </div>
        {salesPlaybooksQuery.isLoading ? (
          <LoadingState message="Loading sales playbooks..." />
        ) : salesPlaybooksQuery.isError ? (
          <ErrorState message={getErrorMessage(salesPlaybooksQuery.error)} />
        ) : (salesPlaybooksQuery.data ?? []).length === 0 ? (
          <EmptyState message="No sales playbooks yet." />
        ) : (
          <ul className="report-list">
            {(salesPlaybooksQuery.data ?? []).map((playbook) => (
              <li key={playbook.id}>
                <Link to={`/sales-playbooks/${playbook.id}`} className="report-list-item">
                  <span>{playbook.strategy_summary ?? "Sales Playbook"}</span>
                  <span>{new Date(playbook.created_at).toLocaleString()}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Meeting Briefs">
        <div className="generate-form">
          <input
            type="text"
            placeholder="Meeting title (optional)"
            value={meetingTitle}
            onChange={(event) => setMeetingTitle(event.target.value)}
          />
          <button type="button" onClick={handleGenerateBrief} disabled={generateBrief.isPending}>
            {generateBrief.isPending ? "Generating..." : "Generate Meeting Brief"}
          </button>
        </div>
        {meetingBriefsQuery.isLoading ? (
          <LoadingState message="Loading meeting briefs..." />
        ) : meetingBriefsQuery.isError ? (
          <ErrorState message={getErrorMessage(meetingBriefsQuery.error)} />
        ) : (meetingBriefsQuery.data ?? []).length === 0 ? (
          <EmptyState message="No meeting briefs yet." />
        ) : (
          <ul className="report-list">
            {(meetingBriefsQuery.data ?? []).map((brief) => (
              <li key={brief.id}>
                <Link to={`/meeting-briefs/${brief.id}`} className="report-list-item">
                  <span>{brief.meeting_title ?? "Meeting Brief"}</span>
                  <span>{new Date(brief.created_at).toLocaleString()}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Outreach Drafts">
        <p className="card-description">
          Generate a draft first - no executive or contact info needed. Choose who it's for and send it later,
          from the draft itself.
        </p>
        <div className="generate-form generate-form-outreach">
          <select value={outreachType} onChange={(event) => setOutreachType(event.target.value)}>
            {OUTREACH_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <select value={executiveName} onChange={(event) => setExecutiveName(event.target.value)}>
            <option value="">Executive (optional)</option>
            {(intelligence?.executives ?? []).map((executive) => (
              <option key={executive.id} value={executive.name}>
                {executive.name}
                {executive.title ? ` - ${executive.title}` : ""}
              </option>
            ))}
          </select>
          <select value={outreachOpportunityId} onChange={(event) => setOutreachOpportunityId(event.target.value)}>
            <option value="">Related opportunity (optional)</option>
            {(trends?.top_opportunities ?? []).map((opportunity) => (
              <option key={opportunity.id} value={opportunity.id}>
                {opportunity.title}
              </option>
            ))}
          </select>
          <select
            value={outreachMeetingBriefId}
            onChange={(event) => setOutreachMeetingBriefId(event.target.value)}
          >
            <option value="">Related meeting brief (optional)</option>
            {(meetingBriefsQuery.data ?? []).map((brief) => (
              <option key={brief.id} value={brief.id}>
                {brief.meeting_title ?? "Meeting Brief"}
              </option>
            ))}
          </select>
          <textarea
            placeholder="Talking points, one per line (optional)"
            value={talkingPointsText}
            onChange={(event) => setTalkingPointsText(event.target.value)}
            rows={3}
          />
          <button type="button" onClick={handleGenerateDraft} disabled={generateDraft.isPending}>
            {generateDraft.isPending ? "Generating..." : "Generate Outreach Draft"}
          </button>
        </div>
        {outreachDraftsQuery.isLoading ? (
          <LoadingState message="Loading outreach drafts..." />
        ) : outreachDraftsQuery.isError ? (
          <ErrorState message={getErrorMessage(outreachDraftsQuery.error)} />
        ) : (outreachDraftsQuery.data ?? []).length === 0 ? (
          <EmptyState message="No outreach drafts yet." />
        ) : (
          <ul className="report-list">
            {(outreachDraftsQuery.data ?? []).map((draft) => (
              <li key={draft.id}>
                <Link to={`/outreach-drafts/${draft.id}`} className="report-list-item">
                  <span>
                    {draft.type} — {draft.subject ?? "(no subject)"}
                  </span>
                  <Badge
                    label={draft.status}
                    variant={outreachStatusVariant(draft.status)}
                  />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="V3 Reports">
        <div className="generate-form">
          <input
            type="text"
            placeholder="Report title (optional)"
            value={reportTitle}
            onChange={(event) => setReportTitle(event.target.value)}
          />
          <button type="button" onClick={handleGenerateReport} disabled={generateReport.isPending}>
            {generateReport.isPending ? "Generating..." : "Generate V3 Report"}
          </button>
        </div>
        {v3ReportsQuery.isLoading ? (
          <LoadingState message="Loading reports..." />
        ) : v3ReportsQuery.isError ? (
          <ErrorState message={getErrorMessage(v3ReportsQuery.error)} />
        ) : (v3ReportsQuery.data ?? []).length === 0 ? (
          <EmptyState message="No V3 reports yet." />
        ) : (
          <ul className="report-list">
            {(v3ReportsQuery.data ?? []).map((report) => (
              <li key={report.id}>
                <Link to={`/v3-reports/${report.id}`} className="report-list-item">
                  <span>{report.title ?? "Report"}</span>
                  <span>{new Date(report.created_at).toLocaleString()}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
