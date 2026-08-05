import { useMutation, useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// The single analysis action. Replaces useAnalyzeCompany, which called
// V2's POST /companies/{id}/analyze and so published a Report on every
// run, and which invalidated only reports and trends - leaving every
// Company Intelligence section on screen showing pre-run data until the
// page was reloaded. That combination is what made "Refresh
// Intelligence" look like it generated a report instead of refreshing
// anything.
//
// The invalidation list below is deliberately the *whole* set of queries
// a run can change. A partial list is what caused the original bug, and
// a missing key fails silently - the section simply keeps rendering
// stale data - so anything the pipeline writes belongs here.
export function useRefreshIntelligence(companyId: string | undefined) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => companyService.refreshCompanyIntelligence(companyId as string),
    onSuccess: () => {
      const scoped = [
        "company", // headline fields and last-analysed timestamp
        "company-intelligence", // signals and business initiatives
        "company-executives", // key people, ranked paths, org map
        "company-technologies", // technology stack
        "company-snapshots", // the intelligence timeline
        "company-trends",
        "company-visual-trends",
        "refresh-summary", // the "What changed" card
      ];
      for (const key of scoped) {
        void queryClient.invalidateQueries({ queryKey: [key, companyId] });
      }
      // Not company-scoped: a run scores opportunities and the pipeline
      // generates notifications, both of which surface globally.
      void queryClient.invalidateQueries({ queryKey: ["opportunity-rankings"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      void queryClient.invalidateQueries({ queryKey: ["executive-dashboard"] });
    },
  });
}
