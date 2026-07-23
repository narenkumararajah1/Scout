// Sales Enablement hub (V2->V3 parity pass, Project Decisions #5/#7/#8).
// Sales Playbooks, Meeting Briefs, Outreach Drafts, and V3 Reports were
// flagship V3 capabilities with no top-level presence - a first-time
// user had no way to discover they existed short of opening a company
// and scrolling. This page surfaces what each capability is and, once
// a company is picked, lists that company's items via the same
// per-company endpoints Company Details already uses (no new backend
// work). Generation stays on Company Details, where the opportunity/
// executive context those forms need already lives - this page links
// there rather than duplicating it.
import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useCompanies } from "../hooks/useCompanies";
import { useCompanyReports } from "../hooks/useCompanyReports";
import { useMeetingBriefs } from "../hooks/useMeetingBriefs";
import { useOutreachDrafts } from "../hooks/useOutreachDrafts";
import { useSalesPlaybooks } from "../hooks/useSalesPlaybooks";
import { useV3Reports } from "../hooks/useV3Reports";
import { getErrorMessage } from "../utils/errors";
import { outreachStatusVariant } from "../utils/outreachDraft";

export function SalesEnablementPage() {
  const companiesQuery = useCompanies();
  const [companyId, setCompanyId] = useState<string | undefined>(undefined);
  const companies = companiesQuery.data ?? [];

  const reportsQuery = useCompanyReports(companyId);
  const salesPlaybooksQuery = useSalesPlaybooks(companyId);
  const meetingBriefsQuery = useMeetingBriefs(companyId);
  const outreachDraftsQuery = useOutreachDrafts(companyId);
  const v3ReportsQuery = useV3Reports(companyId);

  return (
    <div className="sales-enablement-page">
      <h1>Sales Enablement</h1>
      <p className="card-description">
        Scout can generate Sales Playbooks (strategy for a specific opportunity), Meeting Briefs (prep for an
        upcoming conversation), Outreach Drafts (email/message copy for a reviewer to approve), and V3 Reports
        (a full assembled summary), on top of the research Reports it's always produced. Pick a company below to
        browse what's already been generated, or open the company's page to generate something new.
      </p>

      <Card title="Choose a company">
        {companiesQuery.isLoading ? (
          <LoadingState />
        ) : companiesQuery.isError ? (
          <ErrorState message={getErrorMessage(companiesQuery.error)} />
        ) : companies.length === 0 ? (
          <EmptyState message="No companies yet - add one from the Companies page first." />
        ) : (
          <select value={companyId ?? ""} onChange={(event) => setCompanyId(event.target.value || undefined)}>
            <option value="">Choose a company...</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        )}
        {companyId && (
          <p className="card-description">
            <Link to={`/companies/${companyId}`}>Open this company's full page to generate something new →</Link>
          </p>
        )}
      </Card>

      {companyId && (
        <>
          <Card title="Reports">
            {reportsQuery.isLoading ? (
              <LoadingState message="Loading reports..." />
            ) : reportsQuery.isError ? (
              <ErrorState message={getErrorMessage(reportsQuery.error)} />
            ) : (reportsQuery.data ?? []).length === 0 ? (
              <EmptyState message="No reports yet for this company." />
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
            {salesPlaybooksQuery.isLoading ? (
              <LoadingState message="Loading sales playbooks..." />
            ) : salesPlaybooksQuery.isError ? (
              <ErrorState message={getErrorMessage(salesPlaybooksQuery.error)} />
            ) : (salesPlaybooksQuery.data ?? []).length === 0 ? (
              <EmptyState message="No sales playbooks yet for this company." />
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
            {meetingBriefsQuery.isLoading ? (
              <LoadingState message="Loading meeting briefs..." />
            ) : meetingBriefsQuery.isError ? (
              <ErrorState message={getErrorMessage(meetingBriefsQuery.error)} />
            ) : (meetingBriefsQuery.data ?? []).length === 0 ? (
              <EmptyState message="No meeting briefs yet for this company." />
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
            {outreachDraftsQuery.isLoading ? (
              <LoadingState message="Loading outreach drafts..." />
            ) : outreachDraftsQuery.isError ? (
              <ErrorState message={getErrorMessage(outreachDraftsQuery.error)} />
            ) : (outreachDraftsQuery.data ?? []).length === 0 ? (
              <EmptyState message="No outreach drafts yet for this company." />
            ) : (
              <ul className="report-list">
                {(outreachDraftsQuery.data ?? []).map((draft) => (
                  <li key={draft.id}>
                    <Link to={`/outreach-drafts/${draft.id}`} className="report-list-item">
                      <span>
                        {draft.type} - {draft.subject ?? "(no subject)"}
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
            {v3ReportsQuery.isLoading ? (
              <LoadingState message="Loading V3 reports..." />
            ) : v3ReportsQuery.isError ? (
              <ErrorState message={getErrorMessage(v3ReportsQuery.error)} />
            ) : (v3ReportsQuery.data ?? []).length === 0 ? (
              <EmptyState message="No V3 reports yet for this company." />
            ) : (
              <ul className="report-list">
                {(v3ReportsQuery.data ?? []).map((report) => (
                  <li key={report.id}>
                    <Link to={`/v3-reports/${report.id}`} className="report-list-item">
                      <span>{report.title ?? "V3 Report"}</span>
                      <span>{new Date(report.created_at).toLocaleString()}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
