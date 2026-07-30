// How much Scout knows about a company, run over run (V3 Enhancements
// Phase 5 - docs/v3-enhancements/09_VISUAL_INTELLIGENCE.md's "Business
// Trends": "Scout should visualize company evolution over time").
//
// Plots the counts captured by each analysis run: signals, opportunities,
// and the people found. Rising opportunity and executive counts are the
// growth indicator the roadmap asks for, measured in what Scout actually
// holds rather than in revenue or headcount figures it does not have.
//
// **Executives render as a gap, not a zero, before Phase 4A.** Snapshots
// captured before executives existed have a null count, and recharts
// skips nulls with `connectNulls={false}` - so the line starts where the
// data starts. Substituting 0 would draw a rise from "no executives" to
// "three executives" that describes when Scout started looking, not
// anything the company did.
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

interface IntelligenceVolumeChartProps {
  captures: CapturePoint[];
  hasHistory: boolean;
}

const SERIES = [
  { key: "opportunity_count", label: "Opportunities", color: "#4338ca" },
  { key: "signal_count", label: "Signals", color: "#0f766e" },
  { key: "executive_count", label: "People", color: "#b45309" },
] as const;


export function IntelligenceVolumeChart({ captures, hasHistory }: IntelligenceVolumeChartProps) {
  if (!hasHistory) {
    return (
      <EmptyState message="Not enough history yet - Scout needs at least two analysis runs before it can show a trend." />
    );
  }

  const labels = captureLabels(captures);
  const data = captures.map((capture, index) => ({
    date: labels[index],
    opportunity_count: capture.opportunity_count,
    signal_count: capture.signal_count,
    executive_count: capture.executive_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" fontSize={12} />
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
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
