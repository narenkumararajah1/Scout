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

// Priority 6 (production safety) - "clear indication when SMTP is
// enabled" and "environment banner when using live email".
export interface DeliveryStatus {
  environment: string;
  dry_run: boolean;
  smtp_configured: boolean;
  teams_configured: boolean;
  email_live: boolean;
  teams_live: boolean;
}

export interface SystemStatus {
  health: HealthStatus;
  scheduler: SchedulerStatus;
  delivery: DeliveryStatus;
}
