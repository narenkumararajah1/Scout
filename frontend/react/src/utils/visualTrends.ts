// Shared axis labelling for the company trend charts (V3 Enhancements
// Phase 5). Lives here rather than in either chart because both plot the
// same captures on the same axis - if they formatted independently, two
// charts stacked on one page could label the same analysis run
// differently.
import type { CapturePoint } from "../types/visualTrends";

/** Labels for each capture, disambiguating runs that share a date.
 *
 * Date alone is the readable default, but it is genuinely ambiguous:
 * several analyses of one company on the same day is the normal case for
 * a scheduled refresh, and an axis reading "Jul 29, Jul 29, Jul 29" tells
 * a reader nothing about which point is which. Time is appended only to
 * the dates that actually repeat, so the common case stays uncluttered.
 */
export function captureLabels(captures: CapturePoint[]): string[] {
  const dates = captures.map((capture) => new Date(capture.captured_at));
  const dayLabels = dates.map((date) =>
    date.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
  );

  const seen = new Map<string, number>();
  for (const label of dayLabels) {
    seen.set(label, (seen.get(label) ?? 0) + 1);
  }

  return dayLabels.map((label, index) =>
    (seen.get(label) ?? 0) > 1
      ? `${label} ${dates[index].toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`
      : label,
  );
}
