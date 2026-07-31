// A company's technology stack, grouped by how well Scout knows each
// entry rather than listed flat.
//
// **This replaces two flat surfaces, it does not join them.** Company
// Details previously showed technologies twice: a bare "Name - Category"
// list inside Company Intelligence, and a category bar chart under
// Trends. Both counted a single sighting exactly like a technology seen
// in every analysis, which is precisely the distinction Technology
// Intelligence exists to make - on the live NVIDIA data, 63 of 79
// technologies have been seen once, so a flat count is dominated by
// sampling noise rather than by the company's actual stack.
//
// **Established leads, and the long tail collapses.** Rendering all 79
// flat would bury the five technologies Scout has seen every single time
// under sixty-three it has seen once. Established and Emerging are always
// visible; Newly detected and Not-observed-recently sit behind a
// disclosure, the same treatment RefreshSummaryCard gives minor changes.
//
// **Every group carries the backend's own wording.** The lifecycle
// descriptions are not re-written here: they encode claims Scout must not
// overstate - especially that "not observed recently" is not evidence a
// company stopped using something - and re-phrasing them in the UI is
// exactly how that care would get lost.
import { useState } from "react";
import { Badge } from "./Badge";
import { Card } from "./Card";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";
import type { TechnologyIntelligence, TechnologyLifecycle } from "../../types/technologyIntelligence";

interface TechnologyStackProps {
  technologies: TechnologyIntelligence[] | undefined;
  isLoading?: boolean;
  error?: unknown;
  errorMessage?: string;
}

// Order is the reading order: what Scout is most sure of first. Not
// alphabetical and not by count - a user scanning this wants the core
// stack before the long tail.
const GROUP_ORDER: TechnologyLifecycle[] = ["established", "emerging", "newly_detected", "stale"];

// Which groups are worth a user's attention by default. The other two are
// real information, but they are the tail rather than the answer.
const ALWAYS_VISIBLE: TechnologyLifecycle[] = ["established", "emerging"];

function TechnologyGroup({ technologies }: { technologies: TechnologyIntelligence[] }) {
  if (technologies.length === 0) {
    return null;
  }
  // Taken from the first entry rather than a local map - see the note in
  // the module docstring about not re-writing the backend's wording.
  const { lifecycle_label: label, lifecycle_description: description } = technologies[0];

  return (
    <section className="technology-group">
      <h4>
        {label}
        <span className="technology-group-count">{technologies.length}</span>
      </h4>
      <p className="technology-group-description">{description}</p>
      <ul>
        {technologies.map((technology) => (
          <li key={technology.id} className="technology-row">
            <span className="technology-name">{technology.name}</span>
            {technology.category && <Badge label={technology.category} />}
            {/* The evidence, not just the verdict. "Seen in 3 of the 3
                analyses" is checkable; a lifecycle label alone asks the
                user to take Scout's word for it. */}
            <span className="technology-evidence">{technology.evidence_summary}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function TechnologyStack({ technologies, isLoading, error, errorMessage }: TechnologyStackProps) {
  const [showTail, setShowTail] = useState(false);

  if (isLoading) {
    return (
      <Card title="Technology Stack">
        <LoadingState message="Loading technologies..." />
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Technology Stack">
        <ErrorState message={errorMessage ?? "Could not load technologies."} />
      </Card>
    );
  }

  const all = technologies ?? [];
  if (all.length === 0) {
    return (
      <Card title="Technology Stack">
        <EmptyState message="No technologies detected yet. Scout finds these during analysis." />
      </Card>
    );
  }

  const grouped = GROUP_ORDER.map((lifecycle) => ({
    lifecycle,
    items: all.filter((technology) => technology.lifecycle === lifecycle),
  }));
  const visible = grouped.filter((group) => ALWAYS_VISIBLE.includes(group.lifecycle));
  const tail = grouped.filter((group) => !ALWAYS_VISIBLE.includes(group.lifecycle));
  const tailCount = tail.reduce((total, group) => total + group.items.length, 0);
  const confident = visible.reduce((total, group) => total + group.items.length, 0);

  return (
    <Card title="Technology Stack">
      <p className="card-description">
        Grouped by how consistently Scout has seen each technology across analyses. Repetition is what
        separates a company&rsquo;s core stack from a single mention.
      </p>

      {/* The honest headline when a company is new: nothing is confirmed
          yet, and saying so beats an empty-looking card the user cannot
          interpret. */}
      {confident === 0 && (
        <p className="technology-note">
          Nothing confirmed yet — every technology below has been seen only once. Confidence builds as Scout
          analyses this company again.
        </p>
      )}

      {visible.map((group) => (
        <TechnologyGroup key={group.lifecycle} technologies={group.items} />
      ))}

      {tailCount > 0 && (
        <>
          <button type="button" className="technology-tail-toggle" onClick={() => setShowTail((open) => !open)}>
            {showTail
              ? "Hide single sightings"
              : `Show ${tailCount} technolog${tailCount === 1 ? "y" : "ies"} Scout is less sure of`}
          </button>
          {showTail &&
            tail.map((group) => (
              <TechnologyGroup key={group.lifecycle} technologies={group.items} />
            ))}
        </>
      )}
    </Card>
  );
}
