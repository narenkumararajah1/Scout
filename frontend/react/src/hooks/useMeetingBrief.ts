import { useQuery } from "@tanstack/react-query";
import { meetingBriefService } from "../services/meetingBriefService";

export function useMeetingBrief(briefId: string | undefined) {
  return useQuery({
    queryKey: ["meeting-brief", briefId],
    queryFn: () => meetingBriefService.get(briefId as string),
    enabled: briefId !== undefined,
  });
}
