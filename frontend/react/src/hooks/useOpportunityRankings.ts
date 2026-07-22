import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "../services/analyticsService";

export function useOpportunityRankings(limit = 20) {
  return useQuery({
    queryKey: ["opportunity-rankings", limit],
    queryFn: () => analyticsService.opportunityRankings(limit),
  });
}
