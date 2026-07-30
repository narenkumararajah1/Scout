// Signal categories over time (V3 Enhancements Phase 5 -
// docs/v3-enhancements/09_VISUAL_INTELLIGENCE.md).
//
// This is the roadmap's "hiring trends" and "executive movement"
// deliverables, and it needed no new data collection: `Signal.type` has
// carried leadership/hiring/technology/strategic since V2, and Phase 2A
// has been capturing those signals into a snapshot on every analysis run
// ever since. Nothing plotted them until now.
//
// One line per category rather than a stacked area: the question a
// salesperson asks is "is hiring picking up", which is about one
// category's own direction. Stacking makes each band's slope depend on
// the bands beneath it, so a flat category looks like it is moving.
//
// Categories are fixed by the backend rather than derived from the data,
// so a category that drops to zero keeps its line - its decline is the
// finding - and keeps the same colour between renders.
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "../ui/EmptyState";
import type { CapturePoint } from "../../types/visualTrends";
import { captureLabels } from "../../utils/visualTrends";

interface SignalCategoryTrendChartProps {
  captures: CapturePoint[];
  hasHistory: boolean;
}

// Semantic rather than decorative: leadership and hiring are the two
// categories that most often precede a buying decision, so they get the
// strongest colours and the rest recede.
const SERIES = [
  { key: "leadership", label: "Leadership", color: "#4338ca" },
  { key: "hiring", label: "Hiring", color: "#0f766e" },
  { key: "technology", label: "Technology", color: "#b45309" },
  { key: "strategic", label: "Strategic", color: "#6b7280" },
] as const;


export function SignalCategoryTrendChart({ captures, hasHistory }: SignalCategoryTrendChartProps) {
  if (!hasHistory) {
    // Deliberately not a chart. A line through one point invites the
    // reader to see a direction the data does not contain, and the fix
    // is to say what would make it a trend.
    return (
      <EmptyState message="Not enough history yet - Scout needs at least two analysis runs before it can show a trend." />
    );
  }

  const labels = captureLabels(captures);
  const data = captures.map((capture, index) => ({
    date: labels[index],
    leadership: capture.leadership,
    hiring: capture.hiring,
    technology: capture.technology,
    strategic: capture.strategic,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" fontSize={12} />
        {/* Signal counts are whole numbers; the default tick formatter
            would otherwise offer 0.5 of a signal on a short axis. */}
        <YAxis allowDecimals={false} fontSize={12} />
        <Tooltip />
        <Legend />
        {SERIES.map((series) => (
          <Line
            key={series.key}
            type="monotone"
            dataKey={series.key}
            name={series.label}
            stroke={series.color}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
