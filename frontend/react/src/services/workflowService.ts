// Workflow run history domain operations (V2->V3 parity pass). Wraps
// V2's existing, unversioned GET /workflow/history
// (backend/routers/workflow.py) - the same endpoint V2's System Status
// and Reports pages already read from, most recent run first.
import { apiRequest } from "../api/client";
import type { WorkflowRun } from "../types/workflow";

export const workflowService = {
  async getHistory(): Promise<WorkflowRun[]> {
    return apiRequest<WorkflowRun[]>("/workflow/history");
  },
};
