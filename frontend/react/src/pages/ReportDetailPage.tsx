// Displays a V2 Report exactly as generated - reads only, never
// regenerates or edits intelligence (backend/models/report.py's Report
// is immutable by design). Distribution sends this report to every
// eligible recipient across their preferred channels - a real,
// irreversible send, gated behind an explicit confirmation dialog.
import { Link, useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useConfirm } from "../hooks/useConfirm";
import { useDistributeReport } from "../hooks/useDistributeReport";
import { useReport } from "../hooks/useReport";
import { useReportDeliveries } from "../hooks/useReportDeliveries";
import { useToasts } from "../hooks/useToasts";
import type { Report } from "../types/report";
import { getErrorMessage } from "../utils/errors";

const REPORT_SECTIONS: Array<{ key: keyof Report; label: string }> = [
  { key: "executive_summary", label: "Executive Summary" },
  { key: "company_overview", label: "Company Overview" },
  { key: "key_findings", label: "Key Findings" },
  { key: "technology_analysis", label: "Technology Analysis" },
  { key: "capability_alignment", label: "Capability Alignment" },
  { key: "opportunities_section", label: "Opportunities" },
  { key: "recommendations", label: "Recommendations" },
  { key: "talking_points", label: "Talking Points" },
];

export function ReportDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const reportQuery = useReport(reportId);
  const deliveriesQuery = useReportDeliveries(reportId);
  const distributeReport = useDistributeReport(reportId);
  const { toasts, pushToast, dismissToast } = useToasts();
  const { confirm, confirmDialog } = useConfirm();

  async function handleDistribute() {
    if (
      !(await confirm(
        "Send this report to every eligible recipient now? This sends real email/Teams messages and can't be undone.",
      ))
    ) {
      return;
    }
    pushToast("Sending report...", "progress");
    distributeReport.mutate(undefined, {
      onSuccess: (deliveries) => {
        const sent = deliveries.filter((delivery) => delivery.status === "sent").length;
        pushToast(`Distributed to ${sent} of ${deliveries.length} delivery attempt(s).`, "success");
      },
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

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
  const deliveries = deliveriesQuery.data ?? [];

  return (
    <div className="report-detail-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      <Link to={`/companies/${report.company_id}`} className="breadcrumb-back">
        ← Back to company
      </Link>

      <div className="page-header">
        <h1>Report</h1>
        <span className="report-generated-at">Generated {new Date(report.created_at).toLocaleString()}</span>
        <button type="button" onClick={handleDistribute} disabled={distributeReport.isPending}>
          {distributeReport.isPending ? "Sending..." : "Distribute Report"}
        </button>
      </div>

      {REPORT_SECTIONS.map(({ key, label }) => {
        const value = report[key];
        return (
          <Card key={key} title={label}>
            {value ? <p className="report-section-text">{value}</p> : <EmptyState message="Not available." />}
          </Card>
        );
      })}

      <Card title="Delivery History">
        {deliveriesQuery.isLoading ? (
          <LoadingState />
        ) : deliveriesQuery.isError ? (
          <ErrorState message={getErrorMessage(deliveriesQuery.error)} />
        ) : deliveries.length === 0 ? (
          <EmptyState message="This report hasn't been delivered to anyone yet." />
        ) : (
          <ul className="delivery-list">
            {deliveries.map((delivery) => (
              <li key={delivery.id} className="delivery-list-item">
                <span>{delivery.channel}</span>
                <span>{new Date(delivery.delivery_time).toLocaleString()}</span>
                <Badge label={delivery.status} variant={delivery.status === "sent" ? "success" : "neutral"} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
