// Mirrors backend/models/schedule.py's Schedule (V2->V3 parity pass).
export interface Schedule {
  id: string;
  frequency: string;
  time: string;
  enabled: boolean;
  target_company_ids: string[];
  created_at: string;
}

export interface CreateScheduleInput {
  frequency: string;
  time: string;
  target_company_ids: string[];
}

export interface UpdateScheduleInput {
  frequency?: string;
  time?: string;
  target_company_ids?: string[];
}
