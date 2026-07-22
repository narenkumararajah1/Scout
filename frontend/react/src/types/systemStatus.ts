// Mirrors backend/routers/system.py's GET /system/status and
// backend/routers/health.py's GET /health response shapes exactly.

export interface HealthStatus {
  status: string;
  database_connected: boolean;
  chroma_connected: boolean;
}

export interface SchedulerStatus {
  running: boolean;
  interval_hours: number;
  next_run_time: string | null;
}

export interface SystemStatus {
  health: HealthStatus;
  scheduler: SchedulerStatus;
}
