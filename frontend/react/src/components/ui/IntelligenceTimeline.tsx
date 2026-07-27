// Roadmap Phase 5 (Visual Intelligence) - "Timeline of Scout
// Intelligence: opportunity discoveries, score changes, evidence
// collected, recommendations generated." A compact visual event list
// (not a recharts chart - a timeline of discrete events reads better
// as markers than as a plotted metric), merged and sorted server-side
// in backend/services/analytics_service.py's company_trends().
import { EmptyState } from "./EmptyState";

export type TimelineEventType = "research" | "opportunity" | "report";

interface TimelineEvent {
  date: string;
  type: TimelineEventType;
  label: string;
}

const EVENT_LABELS: Record<TimelineEventType, string> = {
  research: "Research",
  opportunity: "Opportunity",
  report: "Report",
};

interface IntelligenceTimelineProps {
  events: TimelineEvent[];
}

export function IntelligenceTimeline({ events }: IntelligenceTimelineProps) {
  if (events.length === 0) {
    return <EmptyState message="No activity recorded yet." />;
  }

  return (
    <ol className="intelligence-timeline">
      {events.map((event, index) => (
        <li key={index} className={`intelligence-timeline-item intelligence-timeline-${event.type}`}>
          <span className="intelligence-timeline-marker" aria-hidden="true" />
          <span className="intelligence-timeline-type">{EVENT_LABELS[event.type]}</span>
          <span className="intelligence-timeline-label">{event.label}</span>
          <span className="intelligence-timeline-date">{new Date(event.date).toLocaleString()}</span>
        </li>
      ))}
    </ol>
  );
}
