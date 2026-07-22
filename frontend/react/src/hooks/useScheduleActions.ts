import { useMutation, useQueryClient } from "@tanstack/react-query";
import { scheduleService } from "../services/scheduleService";
import type { CreateScheduleInput, UpdateScheduleInput } from "../types/schedule";

export function useScheduleActions() {
  const queryClient = useQueryClient();

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["schedules"] });
  }

  const createSchedule = useMutation({
    mutationFn: (input: CreateScheduleInput) => scheduleService.createSchedule(input),
    onSuccess: invalidate,
  });

  const updateSchedule = useMutation({
    mutationFn: ({ scheduleId, input }: { scheduleId: string; input: UpdateScheduleInput }) =>
      scheduleService.updateSchedule(scheduleId, input),
    onSuccess: invalidate,
  });

  const enableSchedule = useMutation({
    mutationFn: (scheduleId: string) => scheduleService.enableSchedule(scheduleId),
    onSuccess: invalidate,
  });

  const disableSchedule = useMutation({
    mutationFn: (scheduleId: string) => scheduleService.disableSchedule(scheduleId),
    onSuccess: invalidate,
  });

  const deleteSchedule = useMutation({
    mutationFn: (scheduleId: string) => scheduleService.deleteSchedule(scheduleId),
    onSuccess: invalidate,
  });

  return { createSchedule, updateSchedule, enableSchedule, disableSchedule, deleteSchedule };
}
