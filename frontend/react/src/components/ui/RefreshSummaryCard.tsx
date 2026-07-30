// The refresh summary (V3 Enhancements Phase 2B -
// docs/v3-enhancements/07_COMPANY_REFRESH_ENGINE.md).
//
// That document calls this "the primary output of Run Analysis", answering
// what changed, why it matters and what to do next. It is a component
// rather than inline markup because CompanyDetailsPage is already ~860
// lines and this has real branching of its own.
//
// Three states, deliberately worded differently, because conflating them
// is misleading:
//   - first refresh   : no baseline existed, so nothing *could* be compared
//   - no changes      : a comparison ran and found nothing move
//   - changes         : the interesting case
//
// Major changes lead and are always visible; minor ones sit behind a
// disclosure. That is the document's own noise instruction applied to
// layout - most refreshes produce a handful of significant changes and a
// longer tail of restatements, and showing all of it flat buries the part
// that matters.
import { useState } from "react";
import { Badge } from "./Badge";
import { Card } from "./Card";
import type { DetectedChange, RefreshSummary } from "../../types/refreshSummary";
import {
  categoryLabel,
  changeTypeLabel,
  changeTypeVariant,
  majorChanges,
  minorChanges,
} from "../../utils/refreshSummary";

interface RefreshSummaryCardProps {
  summary: RefreshSummary | null | undefined;
  isLoading?: boolean;
  // Rendered when the company has never been analysed, so the empty state
  // can offer the action that fixes it rather than being a dead end.
  onRunAnalysis?: () => void;
  isRunning?: boolean;
}

function ChangeRow({ change }: { change: DetectedChange }) {
  return (
    <li className={`refresh-change refresh-change-${change.significance}`}>
      <div className="refresh-change-header">
        <Badge
          label={changeTypeLabel(change.change_type)}
          variant={changeTypeVariant(change.change_type, change.significance)}
        />
        <Badge label={categoryLabel(change.category)} />
        <span className="refresh-change-title">{change.title}</span>
      </div>
      {change.detail && <p className="refresh-change-detail">{change.detail}</p>}
      {/* Only shown when the two values actually differ - a rewording
          stores the two titles here, a score move stores the two scores,
          and printing an unchanged pair would imply a change that did not
          happen. */}
      {change.previous_value && change.current_value && change.previous_value !== change.current_value && (
        <p className="refresh-change-values">
          <span className="refresh-change-was">{change.previous_value}</span>
          <span aria-hidden="true"> → </span>
          <span className="refresh-change-now">{change.current_value}</span>
        </p>
      )}
      {change.source && <p className="refresh-change-source">Detected from {change.source}</p>}
    </li>
  );
}

export function RefreshSummaryCard({
  summary,
  isLoading = false,
  onRunAnalysis,
  isRunning = false,
}: RefreshSummaryCardProps) {
  const [showMinor, setShowMinor] = useState(false);

  if (isLoading) {
    return (
      <Card title="What changed">
        <div className="state state-loading">Loading refresh summary...</div>
      </Card>
    );
  }

  // Never analysed: there is no history to summarise yet.
  if (!summary) {
    return (
      <Card title="What changed">
        <p className="refresh-empty">
          Scout hasn't analysed this company yet. Run an analysis to establish a baseline - after that, every run
          reports what has changed since the last one.
        </p>
        {/* "Run first analysis", not "Refresh Intelligence" as in the page
            header: it is the same action, but there is nothing to refresh
            yet, and reusing the header's exact label would put two
            identically-named buttons on one screen. */}
        {onRunAnalysis && (
          <button type="button" onClick={onRunAnalysis} disabled={isRunning}>
            {isRunning ? "Running first analysis..." : "Run first analysis"}
          </button>
        )}
      </Card>
    );
  }

  const capturedAt = new Date(summary.captured_at).toLocaleString();
  const major = majorChanges(summary.changes);
  const minor = minorChanges(summary.changes);

  return (
    <Card title="What changed">
      <p className="refresh-meta">
        Last refreshed {capturedAt} &middot; {summary.signal_count} signal
        {summary.signal_count === 1 ? "" : "s"}, {summary.opportunity_count} opportunit
        {summary.opportunity_count === 1 ? "y" : "ies"} captured
      </p>

      {/* Suppressed for a first refresh. The meta line above already gives
          when and what was captured, and the hint below explains that this
          is a baseline, so the narrative adds nothing there. It also avoids
          a contradiction on snapshots written before the backend gained a
          dedicated first-refresh narrative: those rows persist the
          no-change wording ("no meaningful changes since the last refresh")
          which reads as false next to the baseline hint. Narratives are
          stored rather than regenerated on purpose, so old rows keep their
          original text. */}
      {summary.narrative && !summary.is_first_refresh && (
        <p className="refresh-narrative">{summary.narrative}</p>
      )}

      {summary.is_first_refresh ? (
        <p className="refresh-hint">
          This was the first analysis, so there was nothing to compare against. The next run will report changes
          against this baseline.
        </p>
      ) : summary.changes.length === 0 ? (
        <p className="refresh-hint">
          Nothing meaningful moved since the previous analysis
          {summary.unchanged.length > 0 && ` - ${summary.unchanged.length} previously known item(s) reconfirmed`}.
        </p>
      ) : (
        <>
          <p className="refresh-counts">
            {summary.changes.length} change{summary.changes.length === 1 ? "" : "s"} detected
            {major.length > 0 && `, ${major.length} significant`}
          </p>

          {major.length > 0 && (
            <ul className="refresh-change-list">
              {major.map((change, index) => (
                <ChangeRow key={`major-${index}`} change={change} />
              ))}
            </ul>
          )}

          {minor.length > 0 && (
            <>
              <button
                type="button"
                className="refresh-toggle-minor"
                onClick={() => setShowMinor((open) => !open)}
                aria-expanded={showMinor}
              >
                {showMinor ? "Hide" : "Show"} {minor.length} lower-significance change
                {minor.length === 1 ? "" : "s"}
              </button>
              {showMinor && (
                <ul className="refresh-change-list">
                  {minor.map((change, index) => (
                    <ChangeRow key={`minor-${index}`} change={change} />
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}

      {summary.recommended_actions.length > 0 && (
        <div className="refresh-actions">
          <h4>Recommended next steps</h4>
          <ol>
            {summary.recommended_actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}
