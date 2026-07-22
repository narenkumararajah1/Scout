import { useQuery } from "@tanstack/react-query";
import { meetingBriefService } from "../services/meetingBriefService";

export function useMeetingBriefs(companyId: string | undefined) {
  return useQuery({
    queryKey: ["meeting-briefs", companyId],
    queryFn: () => meetingBriefService.listForCompany(companyId as string),
    enabled: companyId !== undefined,
  });
}
