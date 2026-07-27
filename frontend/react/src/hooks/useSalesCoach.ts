import { useMutation } from "@tanstack/react-query";
import { companyService } from "../services/companyService";

// Opt-in, not fetched automatically - roadmap Phase 4, item 10 ("AI
// Sales Coach") is a real LLM call each time, so the caller triggers it
// with a button rather than firing it on every page load.
export function useSalesCoach(companyId: string | undefined) {
  return useMutation({
    mutationFn: () => companyService.getSalesCoachRecommendation(companyId as string),
  });
}
