// Key People (V3 Enhancements Phase 4B -
// docs/v3-enhancements/06_LINKEDIN_INTELLIGENCE.md, roadmap Phase 4).
//
// That phase's success criterion is that Scout recommends "not only who
// to contact, but why they matter and the strongest path into the
// organization". So this card leads with the *ranking*, not the roster:
// an alphabetical list of names is what Scout showed before this phase
// and it answers none of that question.
//
// Two views of the same people, because a salesperson asks two different
// questions. "Who do I approach first" is the ranked path, and it is the
// default. "Who else is there" is the org map, one click away. They are
// never shown at once - the same person appearing twice on one screen
// under two orderings reads as duplication rather than as two lenses.
//
// **Every claim here is labelled for what it is.** Seniority and
// department are inferred from job titles, and the LinkedIn links are
// searches rather than verified profiles. 06_LINKEDIN_INTELLIGENCE.md's
// Ethical and Technical Considerations section requires limitations be
// indicated rather than papered over, and a plausible-looking wrong
// answer is worse here than an obviously uncertain one - this ranking
// decides who a salesperson contacts first.
import { useState } from "react";
import { Badge } from "./Badge";
import { Card } from "./Card";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";
import type { Executive, ExecutiveOverview } from "../../types/executive";

interface KeyPeopleProps {
  overview: ExecutiveOverview | undefined;
  isLoading?: boolean;
  error?: unknown;
  errorMessage?: string;
  // Offered in the empty state, so a company with no people yet gets the
  // action that fixes it rather than a dead end.
  onRunAnalysis?: () => void;
  isRunning?: boolean;
}

type View = "paths" | "org";

function seniorityVariant(executive: Executive) {
  if (executive.is_decision_maker) return "success" as const;
  if (executive.seniority_tier === "unknown") return "neutral" as const;
  return "warning" as const;
}

function ExecutiveIdentity({ executive }: { executive: Executive }) {
  return (
    <div className="key-person-identity">
      <span className="key-person-name">{executive.name}</span>
      {executive.title && <span className="key-person-title">{executive.title}</span>}
      <span className="key-person-badges">
        <Badge label={executive.seniority_label} variant={seniorityVariant(executive)} />
        {executive.department && <Badge label={executive.department} />}
      </span>
    </div>
  );
}

function LinkedInLink({ executive }: { executive: Executive }) {
  if (!executive.linkedin_url) {
    return null;
  }
  // Wording depends on what the link actually is. Calling a search
  // "LinkedIn profile" would claim Scout matched this person to an
  // account, which it has not - and the whole reason the link is useful
  // is that LinkedIn shows mutual connections on the page it lands on,
  // which Scout itself cannot see.
  return (
    <a
      className="key-person-linkedin"
      href={executive.linkedin_url}
      target="_blank"
      rel="noreferrer noopener"
    >
      {executive.profile_url_is_search ? "Find on LinkedIn ↗" : "LinkedIn profile ↗"}
    </a>
  );
}

export function KeyPeople({
  overview,
  isLoading,
  error,
  errorMessage,
  onRunAnalysis,
  isRunning,
}: KeyPeopleProps) {
  const [view, setView] = useState<View>("paths");

  if (isLoading) {
    return (
      <Card title="Key People">
        <LoadingState message="Loading people..." />
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Key People">
        <ErrorState message={errorMessage ?? "Could not load people."} />
      </Card>
    );
  }

  const people = overview?.executives ?? [];

  if (people.length === 0) {
    return (
      <Card title="Key People">
        <EmptyState message="Scout hasn't identified anyone at this company yet. People are found during analysis." />
        {onRunAnalysis && (
          <button type="button" onClick={onRunAnalysis} disabled={isRunning}>
            {isRunning ? "Running..." : "Run analysis"}
          </button>
        )}
      </Card>
    );
  }

  const paths = overview?.paths ?? [];
  const orgMap = overview?.org_map ?? [];

  return (
    <Card title="Key People">
      <div className="key-people-header">
        <p className="card-description">
          {people.length} {people.length === 1 ? "person" : "people"} identified,{" "}
          {overview?.decision_maker_count ?? 0} likely to hold budget authority.
        </p>
        <div className="key-people-tabs" role="tablist" aria-label="Key people view">
          <button
            type="button"
            role="tab"
            aria-selected={view === "paths"}
            className={view === "paths" ? "is-active" : ""}
            onClick={() => setView("paths")}
          >
            Best path in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "org"}
            className={view === "org" ? "is-active" : ""}
            onClick={() => setView("org")}
          >
            By function
          </button>
        </div>
      </div>

      {view === "paths" ? (
        <ol className="key-people-paths">
          {paths.map((candidate) => (
            <li key={candidate.executive.id} className="key-person">
              <ExecutiveIdentity executive={candidate.executive} />
              <ul className="key-person-reasons">
                {candidate.reasons.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
              <LinkedInLink executive={candidate.executive} />
            </li>
          ))}
        </ol>
      ) : (
        <div className="key-people-org">
          {orgMap.map((group) => (
            <section key={group.department}>
              <h4>{group.department}</h4>
              <ul>
                {group.executives.map((executive) => (
                  <li key={executive.id} className="key-person">
                    <ExecutiveIdentity executive={executive} />
                    <LinkedInLink executive={executive} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {/* Said once, under the grouping it qualifies, rather than on
              every row: this is a functional grouping read off job
              titles, and no source Scout reads states reporting lines. */}
          <p className="key-people-caveat">
            Grouped by function, most senior first. Job titles are the only source, so this is not a
            reporting hierarchy.
          </p>
        </div>
      )}

      {/* Only in the paths view. The org view carries its own, more
          specific caveat ("job titles are the only source"), and stacking
          both said the same thing twice. */}
      {view === "paths" && people.some((person) => person.is_inferred) && (
        <p className="key-people-caveat">
          Seniority and function are inferred from job titles, not confirmed by the company.
        </p>
      )}
    </Card>
  );
}
