// "Run Scout": refresh intelligence for every company Scout is watching,
// one at a time, through the per-company action that already exists.
//
// **Why the queue is here and not in the backend**, matching the
// reasoning in useBulkIngestion: refreshing N companies is N calls to
// POST /api/v1/companies/{id}/refresh, which already runs the whole
// pipeline and handles its own partial failure. A batch endpoint would
// have to re-orchestrate that server-side and invent its own progress
// and error reporting - duplicating the one thing worth not
// duplicating. Looping over the existing endpoint reuses it exactly and
// gets per-company progress and continue-on-failure for free.
//
// **Why sequential.** One refresh is roughly nine LLM calls. Firing
// seventeen companies at once would exhaust a free-tier rate limit
// within seconds, and the provider fallback chain would then burn
// through its backups on work that could simply have waited. Sequential
// is slower and finishes; parallel is faster and fails.
import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { companyService } from "../services/companyService";
import { getErrorMessage } from "../utils/errors";
import type { Company } from "../types/company";

export type RunScoutStatus = "queued" | "running" | "refreshed" | "failed";

export interface RunScoutCompanyResult {
  companyId: string;
  name: string;
  status: RunScoutStatus;
  detail?: string;
}

export interface RunScoutSummary {
  total: number;
  refreshed: number;
  failed: number;
  elapsedMs: number;
  cancelled: boolean;
}

/** Archived companies are excluded (they are hidden from the list and not
 *  being tracked), and so are ones with monitoring disabled - "disabled"
 *  is the user's explicit instruction to leave a company alone, and a
 *  global run must not override it. */
export function eligibleForRunScout(companies: Company[]): Company[] {
  return companies.filter((c) => !c.archived_at && c.monitoring_status === "enabled");
}

export function useRunScout() {
  const queryClient = useQueryClient();
  const [results, setResults] = useState<RunScoutCompanyResult[]>([]);
  const [summary, setSummary] = useState<RunScoutSummary | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const cancelRef = useRef(false);

  const cancel = useCallback(() => {
    // Takes effect between companies, never mid-refresh: a half-cancelled
    // pipeline run would leave the company in a worse state than either
    // finishing or never starting.
    cancelRef.current = true;
  }, []);

  const reset = useCallback(() => {
    setResults([]);
    setSummary(null);
  }, []);

  const run = useCallback(
    async (companies: Company[]) => {
      const queue = eligibleForRunScout(companies);
      if (queue.length === 0 || isRunning) {
        return null;
      }

      cancelRef.current = false;
      setIsRunning(true);
      setSummary(null);
      setResults(queue.map((c) => ({ companyId: c.id, name: c.name, status: "queued" as const })));

      const started = Date.now();
      let refreshed = 0;
      let failed = 0;

      const mark = (companyId: string, status: RunScoutStatus, detail?: string) =>
        setResults((prev) =>
          prev.map((r) => (r.companyId === companyId ? { ...r, status, detail } : r)),
        );

      for (const company of queue) {
        if (cancelRef.current) break;
        mark(company.id, "running");
        try {
          await companyService.refreshCompanyIntelligence(company.id);
          refreshed += 1;
          mark(company.id, "refreshed");
          // Per company, so a long run updates the page as it goes rather
          // than staying stale until the very end.
          void queryClient.invalidateQueries({ queryKey: ["refresh-summary", company.id] });
          void queryClient.invalidateQueries({ queryKey: ["company-intelligence", company.id] });
        } catch (error) {
          // Continue: one company's upstream failure must not abandon the
          // rest of the batch.
          failed += 1;
          mark(company.id, "failed", getErrorMessage(error));
        }
      }

      const done: RunScoutSummary = {
        total: queue.length,
        refreshed,
        failed,
        elapsedMs: Date.now() - started,
        cancelled: cancelRef.current,
      };
      setSummary(done);
      setIsRunning(false);

      // The list itself, plus everything a batch of runs can move.
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      void queryClient.invalidateQueries({ queryKey: ["opportunity-rankings"] });
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      void queryClient.invalidateQueries({ queryKey: ["executive-dashboard"] });

      return done;
    },
    [isRunning, queryClient],
  );

  return { run, cancel, reset, results, summary, isRunning };
}
