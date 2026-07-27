// Roadmap Phase 5 (Visual Intelligence) - "Opportunity Distribution"
// buckets opportunities into the roadmap's own named categories (AI,
// Cloud, Platform Engineering, Data, Security, Digital Experience).
// Deterministic keyword matching over each opportunity's already-known
// recommended_services strings - no new backend data or AI call.

const CATEGORY_KEYWORDS: Array<{ category: string; keywords: string[] }> = [
  { category: "AI", keywords: ["ai", "artificial intelligence", "machine learning", "genai", "agentic"] },
  { category: "Security", keywords: ["security", "cyber"] },
  { category: "Data", keywords: ["data"] },
  { category: "Platform Engineering", keywords: ["platform"] },
  { category: "Cloud", keywords: ["cloud"] },
  { category: "Digital Experience", keywords: ["digital experience", "customer experience", "digital customer"] },
];

const OTHER_CATEGORY = "Other";

export function categorizeService(service: string): string {
  const lower = service.toLowerCase();
  for (const { category, keywords } of CATEGORY_KEYWORDS) {
    if (keywords.some((keyword) => lower.includes(keyword))) {
      return category;
    }
  }
  return OTHER_CATEGORY;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export function countByCategory(services: string[]): CategoryCount[] {
  const counts = new Map<string, number>();
  for (const service of services) {
    const category = categorizeService(service);
    counts.set(category, (counts.get(category) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count);
}
