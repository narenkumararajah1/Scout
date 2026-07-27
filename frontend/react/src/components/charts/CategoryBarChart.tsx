// Roadmap Phase 5 (Visual Intelligence) - a generic labeled-count bar
// chart, reused for Opportunity Distribution and Technology Stack
// breakdowns. "Every page should answer a question visually before
// answering it with text" (roadmap's Guiding Principle) - this sits
// above the equivalent text list wherever it's used, never replaces it.
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../ui/EmptyState";

interface CategoryBarChartProps {
  data: Array<{ category: string; count: number }>;
  emptyMessage?: string;
}

export function CategoryBarChart({ data, emptyMessage = "Not enough data yet." }: CategoryBarChartProps) {
  if (data.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 40)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="category" width={140} tick={{ fontSize: 12 }} />
        <Tooltip cursor={{ fill: "#f3f4f6" }} />
        <Bar dataKey="count" fill="#4f46e5" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
