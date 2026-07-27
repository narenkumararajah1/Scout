import { useQuery } from "@tanstack/react-query";
import { analyticsService } from "../services/analyticsService";

export function useExecutiveDashboard(limit = 50) {
  return useQuery({
    queryKey: ["executive-dashboard", limit],
    queryFn: () => analyticsService.executiveDashboard(limit),
  });
}
