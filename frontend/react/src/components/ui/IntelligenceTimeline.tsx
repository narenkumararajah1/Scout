// Roadmap Phase 5 (Visual Intelligence) - a compact visual event list
// (not a recharts chart: a timeline of discrete events reads better as
// markers than as a plotted metric).
//
// V3 Enhancements Phase 2B repointed this at the Company Refresh Engine's
// snapshots. It previously rendered analytics_service.company_trends()'s
// derived timeline, which re-listed individual opportunities and reports -
// both of which already have their own cards on the company page, so the
// timeline was largely restating them. A snapshot is one analysis run and
// carries strictly more: how much Scout knew at that moment and how much
// changed since the run before. The presentation is unchanged; only the
// source of the events moved.
import { EmptyState } from "./EmptyState";

export type TimelineEventType = "research" | "opportunity" | "report" | "refresh";

export interface TimelineEvent {
  date: string;
  type: TimelineEventType;
  label: string;
  // Secondary line, used by refresh events for the change count. Optional
  // so the older event shapes still render unchanged.
  detail?: string | null;
}

const EVENT_LABELS: Record<TimelineEventType, string> = {
  research: "Research",
  opportunity: "Opportunity",
  report: "Report",
  refresh: "Refresh",
};

interface IntelligenceTimelineProps {
  events: TimelineEvent[];
  emptyMessage?: string;
}

export function IntelligenceTimeline({ events, emptyMessage }: IntelligenceTimelineProps) {
  if (events.length === 0) {
    return <EmptyState message={emptyMessage ?? "No activity recorded yet."} />;
  }

  return (
    <ol className="intelligence-timeline">
      {events.map((event, index) => (
        <li key={index} className={`intelligence-timeline-item intelligence-timeline-${event.type}`}>
          <span className="intelligence-timeline-marker" aria-hidden="true" />
          <span className="intelligence-timeline-type">{EVENT_LABELS[event.type]}</span>
          <span className="intelligence-timeline-label">
            {event.label}
            {event.detail && <span className="intelligence-timeline-detail">{event.detail}</span>}
          </span>
          <span className="intelligence-timeline-date">{new Date(event.date).toLocaleString()}</span>
        </li>
      ))}
    </ol>
  );
}
