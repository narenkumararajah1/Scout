// Roadmap Phase 5 (Visual Intelligence) - "Opportunity Trends: Opportunity
// Score history, Confidence history" visualization for the Company
// Details Trends card. Opportunity is immutable per analysis run
// (ADR-018), so every past run's opportunities are still in the
// database - this plots them across their own generated_date, a real
// history rather than a fabricated one.
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../ui/EmptyState";

interface OpportunityTrendChartProps {
  data: Array<{ date: string; confidence_score: number | null; priority: number | null }>;
}

export function OpportunityTrendChart({ data }: OpportunityTrendChartProps) {
  const points = data.filter((item) => item.confidence_score !== null || item.priority !== null);
  if (points.length < 2) {
    return <EmptyState message="Not enough history yet - run analysis a few more times to see a trend." />;
  }

  const chartData = points.map((item) => ({
    date: new Date(item.date).toLocaleDateString(),
    "Confidence (%)": item.confidence_score !== null ? Math.round(item.confidence_score * 100) : null,
    Priority: item.priority,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Line type="monotone" dataKey="Confidence (%)" stroke="#4f46e5" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="Priority" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
