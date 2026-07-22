// Schedule domain operations (V2->V3 parity pass). Wraps the new
// unversioned /schedules/* endpoints (backend/routers/schedule.py) that
// finally read/write the Schedule entity/repository, which existed
// since V2 Phase 2 but nothing ever called - lets admins configure
// delivery frequency/time instead of relying solely on the .env
// scheduler_interval_hours fallback (see backend/scheduler.py).
import { apiRequest } from "../api/client";
import type { CreateScheduleInput, Schedule, UpdateScheduleInput } from "../types/schedule";

export const scheduleService = {
  async listSchedules(): Promise<Schedule[]> {
    return apiRequest<Schedule[]>("/schedules");
  },

  async createSchedule(input: CreateScheduleInput): Promise<Schedule> {
    return apiRequest<Schedule>("/schedules", { method: "POST", body: input });
  },

  async updateSchedule(scheduleId: string, input: UpdateScheduleInput): Promise<Schedule> {
    return apiRequest<Schedule>(`/schedules/${scheduleId}`, { method: "PATCH", body: input });
  },

  async enableSchedule(scheduleId: string): Promise<Schedule> {
    return apiRequest<Schedule>(`/schedules/${scheduleId}/enable`, { method: "POST" });
  },

  async disableSchedule(scheduleId: string): Promise<Schedule> {
    return apiRequest<Schedule>(`/schedules/${scheduleId}/disable`, { method: "POST" });
  },

  async deleteSchedule(scheduleId: string): Promise<void> {
    await apiRequest<void>(`/schedules/${scheduleId}`, { method: "DELETE" });
  },
};
