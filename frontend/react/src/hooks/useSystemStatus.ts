import { useQuery } from "@tanstack/react-query";
import { systemService } from "../services/systemService";

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system-status"],
    queryFn: () => systemService.getStatus(),
  });
}
