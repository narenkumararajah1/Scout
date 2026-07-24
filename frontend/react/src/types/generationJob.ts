// Generic AI generation job (Priority 1). One shape covers every
// generation flow (Sales Playbook, Meeting Brief, Outreach Draft,
// Report) - see backend/schemas/generation_job.py.
export type GenerationJobStatus = "pending" | "running" | "completed" | "failed";

export interface GenerationJob {
  id: string;
  job_type: string;
  status: GenerationJobStatus;
  company_id: string;
  result_id: string | null;
  error_message: string | null;
  progress_message: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
}
