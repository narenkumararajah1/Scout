import type { GenerationJob } from "../../types/generationJob";

interface GenerationStatusProps {
  job: GenerationJob | undefined;
  onRetry?: () => void;
}

// Shared status display for every AI generation flow (Priority 1) -
// Sales Playbook, Meeting Brief, Outreach Draft, Report all render
// this instead of each inventing its own pending/failed presentation.
export function GenerationStatus({ job, onRetry }: GenerationStatusProps) {
  if (!job || job.status === "completed") {
    return null;
  }

  if (job.status === "failed") {
    return (
      <div className="state state-error generation-status">
        <p>{job.error_message ?? "Generation failed."}</p>
        {onRetry && (
          <button type="button" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="state state-loading generation-status">{job.progress_message ?? "Generating..."}</div>
  );
}
