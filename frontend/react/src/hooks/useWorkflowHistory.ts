import { useQuery } from "@tanstack/react-query";
import { workflowService } from "../services/workflowService";

export function useWorkflowHistory() {
  return useQuery({
    queryKey: ["workflow-history"],
    queryFn: () => workflowService.getHistory(),
  });
}
