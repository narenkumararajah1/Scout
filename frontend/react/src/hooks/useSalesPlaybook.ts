import { useQuery } from "@tanstack/react-query";
import { salesPlaybookService } from "../services/salesPlaybookService";

export function useSalesPlaybook(playbookId: string | undefined) {
  return useQuery({
    queryKey: ["sales-playbook", playbookId],
    queryFn: () => salesPlaybookService.get(playbookId as string),
    enabled: playbookId !== undefined,
  });
}
