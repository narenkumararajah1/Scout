// Roadmap Phase 5 (Visual Intelligence) - "Executive Dashboard: Opportunity
// Score, Confidence" visualization. Renders each opportunity's priority
// and confidence side by side so a reader sees the shape of the pipeline
// at a glance, before reading each opportunity's own card/description.
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../ui/EmptyState";

interface OpportunityScoreChartProps {
  data: Array<{ title: string; priority: number | null; confidence_score: number | null }>;
}

const MAX_LABEL_LENGTH = 28;

function truncate(label: string): string {
  return label.length > MAX_LABEL_LENGTH ? `${label.slice(0, MAX_LABEL_LENGTH - 1)}…` : label;
}

export function OpportunityScoreChart({ data }: OpportunityScoreChartProps) {
  if (data.length === 0) {
    return <EmptyState message="No opportunities yet." />;
  }

  const chartData = data.map((item) => ({
    title: truncate(item.title),
    Priority: item.priority ?? 0,
    "Confidence (%)": item.confidence_score !== null ? Math.round(item.confidence_score * 100) : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 44)}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="title" width={180} tick={{ fontSize: 11 }} />
        <Tooltip cursor={{ fill: "#f3f4f6" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Priority" fill="#4f46e5" radius={[0, 4, 4, 0]} />
        <Bar dataKey="Confidence (%)" fill="#a5b4fc" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
