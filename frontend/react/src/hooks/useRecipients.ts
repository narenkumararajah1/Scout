import { useQuery } from "@tanstack/react-query";
import { recipientService } from "../services/recipientService";

export function useRecipients() {
  return useQuery({
    queryKey: ["recipients"],
    queryFn: () => recipientService.listRecipients(),
  });
}
