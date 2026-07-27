import { useEffect, useRef, useState } from "react";
import { companyService } from "../services/companyService";
import type { CompanyVisitChanges } from "../types/companyView";

// Records exactly one visit per companyId per mount (roadmap Phase 3 -
// "What Changed Since Last Visit") - the endpoint isn't idempotent, so
// this can't be a plain useQuery that might refetch on window focus,
// etc. Best-effort: a failure here never blocks the rest of the page.
export function useCompanyVisit(companyId: string | undefined): CompanyVisitChanges | null {
  const [changes, setChanges] = useState<CompanyVisitChanges | null>(null);
  const visitedCompanyId = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!companyId || visitedCompanyId.current === companyId) {
      return;
    }
    visitedCompanyId.current = companyId;
    companyService
      .visitCompany(companyId)
      .then(setChanges)
      .catch(() => undefined);
  }, [companyId]);

  return changes;
}
