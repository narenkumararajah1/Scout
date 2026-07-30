import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { BulletList } from "../components/ui/BulletList";
import { Card } from "../components/ui/Card";
import { OpportunityTrendChart } from "../components/charts/OpportunityTrendChart";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { GenerationStatus } from "../components/ui/GenerationStatus";
import { IntelligenceTimeline } from "../components/ui/IntelligenceTimeline";
import { LoadingState } from "../components/ui/LoadingState";
import { RefreshSummaryCard } from "../components/ui/RefreshSummaryCard";
import { ToastContainer } from "../components/ui/Toast";
import { useAddCompanyRelationship } from "../hooks/useAddCompanyRelationship";
import { useAnalyzeCompany } from "../hooks/useAnalyzeCompany";
import { useArchiveCompany } from "../hooks/useArchiveCompany";
import { useCompanies } from "../hooks/useCompanies";
import { useCompany } from "../hooks/useCompany";
import { useConfirm } from "../hooks/useConfirm";
import { useCompanyIntelligence } from "../hooks/useCompanyIntelligence";
import { useCompanyRelationships } from "../hooks/useCompanyRelationships";
import { useCompanySnapshots } from "../hooks/useCompanySnapshots";
import { useCompanyTrends } from "../hooks/useCompanyTrends";
import { useCompanyVisit } from "../hooks/useCompanyVisit";
import { useGenerateMeetingBrief } from "../hooks/useGenerateMeetingBrief";
import { useGenerateOutreachDraft } from "../hooks/useGenerateOutreachDraft";
import { useGenerateSalesPlaybook } from "../hooks/useGenerateSalesPlaybook";
import { useGenerateV3Report } from "../hooks/useGenerateV3Report";
import { useGenerationJob } from "../hooks/useGenerationJob";
import { useIntelligenceReports } from "../hooks/useIntelligenceReports";
import { useMeetingBriefs } from "../hooks/useMeetingBriefs";
import { useOutreachDrafts } from "../hooks/useOutreachDrafts";
import { useRefreshSummary } from "../hooks/useRefreshSummary";
import { useRemoveCompany } from "../hooks/useRemoveCompany";
import { useRemoveCompanyRelationship } from "../hooks/useRemoveCompanyRelationship";
import { useRestoreCompany } from "../hooks/useRestoreCompany";
import { useSalesCoach } from "../hooks/useSalesCoach";
import { useSalesPlaybooks } from "../hooks/useSalesPlaybooks";
import { useToasts } from "../hooks/useToasts";
import { companyService } from "../services/companyService";
import type { GenerationJob } from "../types/generationJob";
import { RELATIONSHIP_TYPES, type RelationshipType } from "../types/companyRelationship";
import type { TimelineEvent } from "../components/ui/IntelligenceTimeline";
import { getErrorMessage } from "../utils/errors";
import { outreachStatusVariant } from "../utils/outreachDraft";

const RELATIONSHIP_TYPE_LABELS: Record<RelationshipType, string> = {
  competitor: "Competitor",
  partner: "Partner",
  subsidiary: "Subsidiary",
  parent: "Parent Company",
  customer: "Customer",
};

// Priority 1: fires `onCompleted` exactly once, the moment a polled
// GenerationJob first reaches "completed" - shared by all four
// generation flows below instead of each duplicating this transition
// check.
function useOnJobCompleted(job: GenerationJob | undefined, onCompleted: (job: GenerationJob) => void) {
  const seenCompletedIds = useRef(new Set<string>());
  useEffect(() => {
    if (job && job.status === "completed" && !seenCompletedIds.current.has(job.id)) {
      seenCompletedIds.current.add(job.id);
      onCompleted(job);
    }
  }, [job, onCompleted]);
}

const OUTREACH_TYPES = ["Email", "Follow-up", "Meeting Request", "LinkedIn Message"];

export function CompanyDetailsPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const companyQuery = useCompany(companyId);
  const intelligenceQuery = useCompanyIntelligence(companyId);
  const trendsQuery = useCompanyTrends(companyId);
  const salesPlaybooksQuery = useSalesPlaybooks(companyId);
  const meetingBriefsQuery = useMeetingBriefs(companyId);
  const outreachDraftsQuery = useOutreachDrafts(companyId);
  const reportsQuery = useIntelligenceReports(companyId);
  const visitChanges = useCompanyVisit(companyId);
  const refreshSummaryQuery = useRefreshSummary(companyId);
  const snapshotsQuery = useCompanySnapshots(companyId);
  const salesCoach = useSalesCoach(companyId);
  const relationshipsQuery = useCompanyRelationships(companyId);
  const allCompaniesQuery = useCompanies();
  const addRelationship = useAddCompanyRelationship(companyId);
  const removeRelationship = useRemoveCompanyRelationship(companyId);
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
  const archiveCompany = useArchiveCompany();
  const restoreCompany = useRestoreCompany();
  const removeCompany = useRemoveCompany();
  const generatePlaybook = useGenerateSalesPlaybook(companyId);
  const generateBrief = useGenerateMeetingBrief(companyId);
  const generateDraft = useGenerateOutreachDraft(companyId);
  const generateReport = useGenerateV3Report(companyId);

  // Priority 1: each generation flow tracks its own job id and polls
  // it until the background worker finishes; onCompleted below
  // invalidates that flow's list query once the real artifact exists.
  const [playbookJobId, setPlaybookJobId] = useState<string>();
  const [briefJobId, setBriefJobId] = useState<string>();
  const [draftJobId, setDraftJobId] = useState<string>();
  const [reportJobId, setReportJobId] = useState<string>();
  const playbookJob = useGenerationJob(playbookJobId);
  const briefJob = useGenerationJob(briefJobId);
  const draftJob = useGenerationJob(draftJobId);
  const reportJob = useGenerationJob(reportJobId);

  useOnJobCompleted(playbookJob.data, () => {
    void queryClient.invalidateQueries({ queryKey: ["sales-playbooks", companyId] });
    pushToast("Sales playbook generated.", "success");
  });
  useOnJobCompleted(briefJob.data, () => {
    void queryClient.invalidateQueries({ queryKey: ["meeting-briefs", companyId] });
    pushToast("Meeting brief generated.", "success");
  });
  useOnJobCompleted(draftJob.data, () => {
    void queryClient.invalidateQueries({ queryKey: ["outreach-drafts", companyId] });
    pushToast("Outreach draft generated.", "success");
  });
  useOnJobCompleted(reportJob.data, () => {
    void queryClient.invalidateQueries({ queryKey: ["v3-reports", companyId] });
    pushToast("Report generated.", "success");
  });

  const [selectedOpportunityId, setSelectedOpportunityId] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [reportTitle, setReportTitle] = useState("");
  const [outreachType, setOutreachType] = useState(OUTREACH_TYPES[0]);
  const [executiveName, setExecutiveName] = useState("");
  const [talkingPointsText, setTalkingPointsText] = useState("");
  const [outreachOpportunityId, setOutreachOpportunityId] = useState("");
  const [outreachMeetingBriefId, setOutreachMeetingBriefId] = useState("");
  const [relationshipType, setRelationshipType] = useState<RelationshipType>("competitor");
  const [relatedCompanyId, setRelatedCompanyId] = useState("");
  const [relatedCompanyName, setRelatedCompanyName] = useState("");
  const [relationshipNotes, setRelationshipNotes] = useState("");

  function handleAddRelationship() {
    if (!relatedCompanyId && !relatedCompanyName.trim()) {
      pushToast("Choose a tracked company or type a name.", "error");
      return;
    }
    addRelationship.mutate(
      {
        relationshipType,
        relatedCompanyId: relatedCompanyId || undefined,
        relatedCompanyName: relatedCompanyId ? undefined : relatedCompanyName.trim(),
        notes: relationshipNotes.trim() || undefined,
      },
      {
        onSuccess: () => {
          setRelatedCompanyId("");
          setRelatedCompanyName("");
          setRelationshipNotes("");
          pushToast("Relationship added.", "success");
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  function handleRemoveRelationship(relationshipId: string) {
    removeRelationship.mutate(relationshipId, {
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleRunAnalysis() {
    pushToast("Refreshing intelligence - this can take a minute.", "progress");
    analyzeCompany.mutate(undefined, {
      onSuccess: () => {
        // POST /companies/{id}/analyze still returns a Report - that V2
        // contract was deliberately preserved in Phase 2A - so the refresh
        // summary has to be refetched rather than read from the response.
        // Snapshots too, since the run added one.
        void queryClient.invalidateQueries({ queryKey: ["refresh-summary", companyId] });
        void queryClient.invalidateQueries({ queryKey: ["company-snapshots", companyId] });
        pushToast("Intelligence refreshed - see what changed below.", "success");
      },
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGeneratePlaybook() {
    if (!selectedOpportunityId) {
      pushToast("Choose an opportunity first.", "error");
      return;
    }
    generatePlaybook.mutate(selectedOpportunityId, {
      onSuccess: (job) => setPlaybookJobId(job.id),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGenerateBrief() {
    generateBrief.mutate(meetingTitle || undefined, {
      onSuccess: (job) => {
        setBriefJobId(job.id);
        setMeetingTitle("");
      },
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleGenerateReport() {
    generateReport.mutate(reportTitle || undefined, {
      onSuccess: (job) => {
        setReportJobId(job.id);
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
    generateDraft.mutate(
      {
        outreachType,
        executiveName: executiveName || undefined,
        talkingPoints,
        opportunityId: outreachOpportunityId || undefined,
        meetingBriefId: outreachMeetingBriefId || undefined,
      },
      {
        onSuccess: (job) => {
          setDraftJobId(job.id);
          setTalkingPointsText("");
        },
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      },
    );
  }

  async function handleArchive() {
    const company = companyQuery.data;
    if (!company) {
      return;
    }
    if (!(await confirm(`Archive ${company.name}? You can restore it later from the Companies list.`))) {
      return;
    }
    archiveCompany.mutate(company.id, {
      onSuccess: () => pushToast(`${company.name} archived.`, "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  function handleRestore() {
    const company = companyQuery.data;
    if (!company) {
      return;
    }
    restoreCompany.mutate(company.id, {
      onSuccess: () => pushToast(`${company.name} restored.`, "success"),
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  async function handlePermanentlyDelete() {
    const company = companyQuery.data;
    if (!company) {
      return;
    }
    if (
      !(await confirm(`Permanently delete ${company.name}? This cannot be undone and all research history will be lost.`))
    ) {
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

  // One timeline entry per analysis run, built from the Company Refresh
  // Engine's snapshots (V3 Enhancements Phase 2B). This replaced
  // company_trends()'s derived timeline, which re-listed individual
  // opportunities and reports that already have their own cards below.
  const refreshTimeline: TimelineEvent[] = (snapshotsQuery.data ?? []).map((snapshot) => ({
    date: snapshot.captured_at,
    type: "refresh",
    label: `${snapshot.signal_count} signal${snapshot.signal_count === 1 ? "" : "s"}, ${
      snapshot.opportunity_count
    } opportunit${snapshot.opportunity_count === 1 ? "y" : "ies"}`,
    // Deliberately not labelled "baseline" for a zero count: that is true
    // of the very first run, but also of a later run where nothing moved,
    // and a history row carries no way to tell those apart.
    detail:
      snapshot.change_count > 0
        ? `${snapshot.change_count} change${snapshot.change_count === 1 ? "" : "s"} detected`
        : "no changes detected",
  }));

  return (
    <div className="company-details-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <Link to="/companies" className="breadcrumb-back">
        ← Companies
      </Link>

      <div className="page-header">
        <h1>{company.name}</h1>
        {company.archived_at ? (
          <Badge label="Archived" variant="neutral" />
        ) : (
          <Badge
            label={company.monitoring_status}
            variant={company.monitoring_status === "enabled" ? "success" : "neutral"}
          />
        )}
        {!company.archived_at && (
          <button type="button" onClick={() => toggleMonitoring.mutate()} disabled={toggleMonitoring.isPending}>
            {company.monitoring_status === "enabled" ? "Disable monitoring" : "Enable monitoring"}
          </button>
        )}
        {company.archived_at ? (
          <>
            <button type="button" onClick={handleRestore} disabled={restoreCompany.isPending}>
              Restore company
            </button>
            <button
              type="button"
              className="company-remove-button"
              onClick={handlePermanentlyDelete}
              disabled={removeCompany.isPending}
            >
              Delete Permanently
            </button>
          </>
        ) : (
          <button
            type="button"
            className="company-remove-button"
            onClick={handleArchive}
            disabled={archiveCompany.isPending}
          >
            Archive company
          </button>
        )}
        {/* "Refresh Intelligence" rather than "Run Analysis": the run now
            updates what Scout knows and reports what changed, and the
            report is a by-product rather than the point
            (07_COMPANY_REFRESH_ENGINE.md, and the wording
            10_NAVIGATION_IMPROVEMENTS.md uses for this action). */}
        <button type="button" onClick={handleRunAnalysis} disabled={analyzeCompany.isPending}>
          {analyzeCompany.isPending ? "Refreshing..." : "Refresh Intelligence"}
        </button>
        <Link to={`/ask-scout?companyId=${company.id}`} className="ask-scout-link-button">
          Ask Scout about {company.name}
        </Link>
      </div>

      {company.archived_at && (
        <p className="archived-banner">
          This company is archived. It's hidden from the default Companies list, but all research, opportunities,
          reports, and generated content are preserved. Restore it at any time.
        </p>
      )}

      {visitChanges &&
        !visitChanges.first_visit &&
        (visitChanges.new_notifications.length > 0 ||
          visitChanges.new_opportunity_count > 0 ||
          visitChanges.new_report_count > 0) && (
          // Scoped to *your absence* - what landed while you were away -
          // whereas the "What changed" card below is about the *company*
          // moving between analysis runs. Two similarly-worded panels
          // would read as one feature duplicated, so this stays counts
          // plus new alert titles and never restates detected changes.
          <div className="since-last-visit-banner">
            <p>
              While you were away{visitChanges.since ? ` (since ${new Date(visitChanges.since).toLocaleString()})` : ""}:{" "}
              {visitChanges.new_opportunity_count > 0 &&
                `${visitChanges.new_opportunity_count} new opportunit${
                  visitChanges.new_opportunity_count === 1 ? "y" : "ies"
                }`}
              {visitChanges.new_opportunity_count > 0 &&
                (visitChanges.new_report_count > 0 || visitChanges.new_notifications.length > 0) &&
                ", "}
              {visitChanges.new_report_count > 0 &&
                `${visitChanges.new_report_count} new report${visitChanges.new_report_count === 1 ? "" : "s"}`}
              {visitChanges.new_report_count > 0 && visitChanges.new_notifications.length > 0 && ", "}
              {visitChanges.new_notifications.length > 0 &&
                `${visitChanges.new_notifications.length} new alert${
                  visitChanges.new_notifications.length === 1 ? "" : "s"
                }`}
              .
            </p>
            {visitChanges.new_notifications.length > 0 && (
              <ul className="since-last-visit-notifications">
                {visitChanges.new_notifications.map((notification) => (
                  <li key={notification.id}>{notification.title}</li>
                ))}
              </ul>
            )}
          </div>
        )}

      {toggleMonitoring.isError && <p className="form-error">{getErrorMessage(toggleMonitoring.error)}</p>}

      {/* Placed above Overview on purpose: 07_COMPANY_REFRESH_ENGINE.md
          makes this the primary output of an analysis run, so it should be
          the first thing read on the page rather than buried under static
          profile fields. */}
      <RefreshSummaryCard
        summary={refreshSummaryQuery.data}
        isLoading={refreshSummaryQuery.isLoading}
        onRunAnalysis={handleRunAnalysis}
        isRunning={analyzeCompany.isPending}
      />

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
          <>
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
            <h4 className="chart-section-title">Opportunity Trends</h4>
            <OpportunityTrendChart data={trends.opportunity_history} />
            <h4 className="chart-section-title">Refresh history</h4>
            <IntelligenceTimeline
              events={refreshTimeline}
              emptyMessage="No analysis runs recorded yet."
            />
          </>
        )}
      </Card>

      <Card title="Related Companies">
        <p className="card-description">
          Competitors, partners, subsidiaries, parent companies, and customers - helping you understand the broader
          ecosystem around this account. User-curated, not AI-generated.
        </p>
        {relationshipsQuery.isLoading ? (
          <LoadingState message="Loading relationships..." />
        ) : relationshipsQuery.isError ? (
          <ErrorState message={getErrorMessage(relationshipsQuery.error)} />
        ) : (relationshipsQuery.data ?? []).length === 0 ? (
          <EmptyState message="No related companies yet." />
        ) : (
          <ul className="relationship-list">
            {(relationshipsQuery.data ?? []).map((relationship) => (
              <li key={relationship.id} className="relationship-list-item">
                <Badge label={RELATIONSHIP_TYPE_LABELS[relationship.relationship_type]} variant="neutral" />
                {relationship.related_company_id ? (
                  <Link to={`/companies/${relationship.related_company_id}`}>
                    {allCompaniesQuery.data?.find((c) => c.id === relationship.related_company_id)?.name ??
                      relationship.related_company_name ??
                      "View company"}
                  </Link>
                ) : (
                  <span>{relationship.related_company_name}</span>
                )}
                {relationship.notes && <span className="relationship-notes">{relationship.notes}</span>}
                <button
                  type="button"
                  className="relationship-remove-button"
                  onClick={() => handleRemoveRelationship(relationship.id)}
                  disabled={removeRelationship.isPending}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="generate-form">
          <select value={relationshipType} onChange={(event) => setRelationshipType(event.target.value as RelationshipType)}>
            {RELATIONSHIP_TYPES.map((type) => (
              <option key={type} value={type}>
                {RELATIONSHIP_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
          <select
            value={relatedCompanyId}
            onChange={(event) => {
              setRelatedCompanyId(event.target.value);
              if (event.target.value) {
                setRelatedCompanyName("");
              }
            }}
          >
            <option value="">Tracked company (optional)...</option>
            {(allCompaniesQuery.data ?? [])
              .filter((c) => c.id !== companyId)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </select>
          <input
            type="text"
            placeholder="Or type a company name"
            value={relatedCompanyName}
            disabled={relatedCompanyId !== ""}
            onChange={(event) => setRelatedCompanyName(event.target.value)}
          />
          <input
            type="text"
            placeholder="Notes (optional)"
            value={relationshipNotes}
            onChange={(event) => setRelationshipNotes(event.target.value)}
          />
          <button type="button" onClick={handleAddRelationship} disabled={addRelationship.isPending}>
            {addRelationship.isPending ? "Adding..." : "Add Relationship"}
          </button>
        </div>
      </Card>

      <Card title="AI Sales Coach">
        <p className="card-description">
          If you were the Account Executive, what would you do next? Scout synthesizes a live recommendation from
          everything it already knows about this company - it's never saved, so ask again any time.
        </p>
        <button type="button" onClick={() => salesCoach.mutate()} disabled={salesCoach.isPending}>
          {salesCoach.isPending ? "Thinking..." : "Get Recommendation"}
        </button>
        {salesCoach.isError && <p className="form-error">{getErrorMessage(salesCoach.error)}</p>}
        {salesCoach.data && (
          <dl className="sales-coach-recommendation">
            <dt>Who to contact</dt>
            <dd>{salesCoach.data.who_to_contact ?? "Not enough information yet."}</dd>
            <dt>Best timing</dt>
            <dd>{salesCoach.data.best_timing ?? "Not enough information yet."}</dd>
            <dt>Best talking points</dt>
            <dd>
              {salesCoach.data.best_talking_points.length === 0 ? (
                "None yet."
              ) : (
                <BulletList items={salesCoach.data.best_talking_points} />
              )}
            </dd>
            <dt>Suggested sequence</dt>
            <dd>
              {salesCoach.data.suggested_sequence.length === 0 ? (
                "None yet."
              ) : (
                <BulletList items={salesCoach.data.suggested_sequence} />
              )}
            </dd>
            <dt>Risks</dt>
            <dd>
              {salesCoach.data.risks.length === 0 ? "None identified." : <BulletList items={salesCoach.data.risks} />}
            </dd>
            <dt>Why Scout recommends this</dt>
            <dd>{salesCoach.data.why ?? "Not enough information yet."}</dd>
          </dl>
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
          <button
            type="button"
            onClick={handleGeneratePlaybook}
            disabled={generatePlaybook.isPending || playbookJob.data?.status === "running"}
          >
            {generatePlaybook.isPending || playbookJob.data?.status === "running"
              ? "Generating..."
              : "Generate Sales Playbook"}
          </button>
        </div>
        <GenerationStatus job={playbookJob.data} onRetry={handleGeneratePlaybook} />
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
          <button
            type="button"
            onClick={handleGenerateBrief}
            disabled={generateBrief.isPending || briefJob.data?.status === "running"}
          >
            {generateBrief.isPending || briefJob.data?.status === "running" ? "Generating..." : "Generate Meeting Brief"}
          </button>
        </div>
        <GenerationStatus job={briefJob.data} onRetry={handleGenerateBrief} />
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
          <button
            type="button"
            onClick={handleGenerateDraft}
            disabled={generateDraft.isPending || draftJob.data?.status === "running"}
          >
            {generateDraft.isPending || draftJob.data?.status === "running" ? "Generating..." : "Generate Outreach Draft"}
          </button>
        </div>
        <GenerationStatus job={draftJob.data} onRetry={handleGenerateDraft} />
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

      <Card title="Intelligence Reports">
        <p className="card-description">
          A complete rollup of everything gathered on this company - research, opportunities, executives, and
          any sales playbooks, meeting briefs, or outreach drafts generated so far.
        </p>
        <div className="generate-form">
          <input
            type="text"
            placeholder="Report title (optional)"
            value={reportTitle}
            onChange={(event) => setReportTitle(event.target.value)}
          />
          <button
            type="button"
            onClick={handleGenerateReport}
            disabled={generateReport.isPending || reportJob.data?.status === "running"}
          >
            {generateReport.isPending || reportJob.data?.status === "running" ? "Generating..." : "Generate Report"}
          </button>
        </div>
        <GenerationStatus job={reportJob.data} onRetry={handleGenerateReport} />
        {reportsQuery.isLoading ? (
          <LoadingState message="Loading reports..." />
        ) : reportsQuery.isError ? (
          <ErrorState message={getErrorMessage(reportsQuery.error)} />
        ) : reportsQuery.data.length === 0 ? (
          <EmptyState message="No reports yet - run an analysis or generate one above." />
        ) : (
          <ul className="report-list">
            {reportsQuery.data.map((report) => (
              <li key={report.id}>
                <Link to={report.to} className="report-list-item">
                  <span>{report.title}</span>
                  <span>{new Date(report.date).toLocaleString()}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
