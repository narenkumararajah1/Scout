// Displays a V2 Report exactly as generated - reads only, never
// regenerates or edits intelligence (backend/models/report.py's Report
// is immutable by design). Distribution (sending this report to
// recipients) is intentionally not exposed here - see TECH_DEBT.md.
import { useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useReport } from "../hooks/useReport";
import { useReportDeliveries } from "../hooks/useReportDeliveries";
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
      <div className="page-header">
        <h1>Report</h1>
        <span className="report-generated-at">Generated {new Date(report.created_at).toLocaleString()}</span>
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
