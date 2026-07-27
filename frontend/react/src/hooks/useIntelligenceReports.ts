// Roadmap Phase 1 (Report System Unification): merges the two existing,
// unchanged report queries (V2's useCompanyReports, V3's useV3Reports)
// into one list so the user sees a single "Intelligence Reports"
// experience instead of choosing between two systems. No backend or
// service change - purely a composition of hooks that already exist.
import { useCompanyReports } from "./useCompanyReports";
import { useV3Reports } from "./useV3Reports";

export interface IntelligenceReportItem {
  id: string;
  title: string;
  date: string;
  to: string;
}

export function useIntelligenceReports(companyId: string | undefined) {
  const v2Query = useCompanyReports(companyId);
  const v3Query = useV3Reports(companyId);

  const v2Items: IntelligenceReportItem[] = (v2Query.data ?? []).map((report) => ({
    id: `v2-${report.id}`,
    title: "Report",
    date: report.created_at,
    to: `/reports/${report.id}`,
  }));
  const v3Items: IntelligenceReportItem[] = (v3Query.data ?? []).map((report) => ({
    id: `v3-${report.id}`,
    title: report.title ?? "Report",
    date: report.created_at,
    to: `/v3-reports/${report.id}`,
  }));

  const items = [...v2Items, ...v3Items].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  return {
    data: items,
    isLoading: v2Query.isLoading || v3Query.isLoading,
    isError: v2Query.isError || v3Query.isError,
    error: v2Query.error ?? v3Query.error,
  };
}
