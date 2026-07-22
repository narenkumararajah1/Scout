// Mirrors backend/workflow/state.py's WorkflowState (V2->V3 parity pass).
export interface WorkflowRun {
  workflow_id: string;
  status: string;
  current_stage: string | null;
  target_company: string | null;
  completed_stages: string[];
  errors: string[];
  created_at: string;
}
