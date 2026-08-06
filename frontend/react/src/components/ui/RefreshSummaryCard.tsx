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
        {/* Same label as the page header, deliberately. This used to read
            "Run first analysis" to avoid two identically-named buttons on
            one screen, but it is the same action on the same company, and
            three names for one thing ("Run first analysis", "Run
            analysis", "Refresh Intelligence") read as three features. One
            action, one name; the surrounding copy supplies the context
            that there is nothing to compare against yet. */}
        {onRunAnalysis && (
          <button type="button" onClick={onRunAnalysis} disabled={isRunning}>
            {isRunning ? "Refreshing..." : "Refresh Intelligence"}
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

      {/* The narrative is no longer rendered here. It is Scout's assessment
          of the account, and the page now opens with it under that name -
          repeating it verbatim two thirds of the way down made the same
          paragraph appear twice on one screen. This card keeps the job its
          title claims: what changed between the last two refreshes. */}

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

    </Card>
  );
}
