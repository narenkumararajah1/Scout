import { useQuery } from "@tanstack/react-query";
import { scheduleService } from "../services/scheduleService";

export function useSchedules() {
  return useQuery({
    queryKey: ["schedules"],
    queryFn: () => scheduleService.listSchedules(),
  });
}
