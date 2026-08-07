// Scout's watch floor.
//
// The concept: this is not a report about Scout's data, it is Scout's
// working surface. Two columns, deliberately asymmetric - the left is the
// judgement Scout has reached, the right is the field it reached it from.
// That is the same skeleton as the login page (claim beside action) doing a
// different job, which is how the application inherits an identity from the
// login screen without copying it.
//
// Three product decisions drive the composition:
//
// 1. Priority, not confidence, is the real signal. Confidence saturates -
//    14 of 25 opportunities sit at exactly 0.95 - so it separates almost
//    nothing. Priority does: 4 of 25 reach the top of the scale. The page
//    is built on the number that carries information.
//
// 2. The watch is the product. Scout's claim is that it monitors
//    continuously, so the set of companies under watch, and their state,
//    belongs on the first screen as a first-class object rather than as a
//    counter reading "19". The grid encodes three real facts per company:
//    whether it has an opportunity at the top of the scale, whether it has
//    unread signals, and whether it has anything open at all.
//
// 3. Evidence is shown only where it exists. Exactly one opportunity in
//    production carries capability matches and supporting signals; the
//    other 24 have empty arrays. So the chain renders when the record is
//    grounded and is absent when it is not, rather than printing zeros and
//    implying Scout looked and found nothing.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useCompanies } from "../hooks/useCompanies";
import { useNotifications } from "../hooks/useNotifications";
import { useOpportunityRankings } from "../hooks/useOpportunityRankings";
import { getErrorMessage } from "../utils/errors";

// The description is model-written prose and runs long. One sentence is the
// briefing; the rest is the company page's job.
function firstSentence(text: string | null, limit = 190): string | null {
  if (!text) return null;
  const trimmed = text.trim();
  const stop = trimmed.search(/\.\s|\.$/);
  const sentence = stop > 40 ? trimmed.slice(0, stop + 1) : trimmed;
  if (sentence.length <= limit) return sentence;
  return `${sentence.slice(0, limit).replace(/[\s,;:-]+\S*$/, "")}…`;
}

// The five kinds the backend actually emits
// (backend/services/notification_service.py). Naming them in the feed is the
// single biggest legibility win available: without it every row opens with
// the same prose and the eye has nothing to sort on.
const EVENT_KINDS: Record<string, string> = {
  opportunity_alert: "Opportunity",
  strategic_initiative: "Strategic move",
  leadership_change: "Leadership",
  hiring_spike: "Hiring",
  ai_initiative: "AI initiative",
};

// The generator prefixes opportunity alerts with a phrase that the kind label
// now states. Carrying both wastes the most valuable line in the row.
const FEED_ROWS = 10;

const REDUNDANT_PREFIX = /^New high-confidence opportunity:\s*/i;

function relativeTime(iso: string | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days}d ago`;
}

export function DashboardPage() {
  const companiesQuery = useCompanies();
  // The feed shows ten, but the count in the rail must not be the page
  // size wearing a number's clothes - production has at least 100 unread,
  // so a limit of 10 made the rail read "10 new signals" forever. 100 is
  // the endpoint's ceiling; the rail counts companies, which is bounded.
  const notificationsQuery = useNotifications({ limit: 100 });
  // 25, not 5: the page states how many opportunities reach the top of the
  // priority scale, and that has to be counted rather than assumed.
  const opportunitiesQuery = useOpportunityRankings(25);

  const companies = companiesQuery.data ?? [];
  const notifications = notificationsQuery.data ?? [];
  const opportunities = opportunitiesQuery.data ?? [];

  const companyNameById = new Map(companies.map((company) => [company.id, company.name]));
  const unreadCount = notifications.filter((notification) => !notification.is_read).length;
  const unreadCompanyIds = new Set(
    notifications.filter((n) => !n.is_read).map((n) => n.company_id),
  );
  const unreadCompanyCount = unreadCompanyIds.size;

  // The backend already ranks these, so rankings[0] *is* the recommendation
  // and the page does not re-rank it.
  const featured = opportunities[0] ?? null;

  const topPriority = opportunities.reduce((best, o) => Math.max(best, o.priority ?? 0), 0);
  const leadOpportunities = opportunities.filter((o) => (o.priority ?? 0) === topPriority);
  const leadCompanyIds = new Set(leadOpportunities.map((o) => o.company_id));
  const openCompanyIds = new Set(opportunities.map((o) => o.company_id));
  // How many open opportunities each company carries. Surfaced on hover in
  // the watch: the grid answers "what is Scout tracking" at rest, and "how
  // much is here" the moment you point at something.
  const openCountByCompany = opportunities.reduce<Map<string, number>>((counts, o) => {
    counts.set(o.company_id, (counts.get(o.company_id) ?? 0) + 1);
    return counts;
  }, new Map());

  // --- the verdict follows your attention --------------------------------
  // Pointing at a company in the watch re-composes the left column as Scout's
  // read on that company. The two halves of this page have always claimed to
  // be one instrument - the conclusion and the field it came from - and this
  // is what actually makes them one: the field is now the control and the
  // verdict is the readout.
  //
  // Nothing here is invented. The preview shows the same ranked record the
  // backend returned; for a company with nothing open it says so, which is a
  // truthful answer rather than a blank panel.
  const [previewId, setPreviewId] = useState<string | null>(null);
  // The first preview switches the left column from its staggered arrival to
  // a fast cross-fade. Re-running a 350ms reading-order stagger on every
  // hover would make the page feel slow and busy; a single 190ms fade reads
  // as "Scout re-focused".
  const [hasPreviewed, setHasPreviewed] = useState(false);
  const intentTimer = useRef<number | undefined>(undefined);

  // Hover intent. Sweeping the pointer across nineteen cells must not strobe
  // the hero, so entering waits ~120ms and leaving waits longer still - long
  // enough to cross the gap between two cells without falling back to the
  // default and snapping forward again.
  const previewCompany = useCallback((companyId: string | null, immediate = false) => {
    window.clearTimeout(intentTimer.current);
    if (immediate) {
      setPreviewId(companyId);
      if (companyId) setHasPreviewed(true);
      return;
    }
    intentTimer.current = window.setTimeout(
      () => {
        setPreviewId(companyId);
        if (companyId) setHasPreviewed(true);
      },
      companyId ? 120 : 260,
    );
  }, []);

  useEffect(() => () => window.clearTimeout(intentTimer.current), []);

  // Rank is the position in the ranking the backend already produced, and a
  // company's record is its best-ranked opportunity - the first one the
  // ranking reaches.
  const rankByOpportunityId = new Map(opportunities.map((o, index) => [o.id, index + 1]));
  const bestByCompany = new Map<string, (typeof opportunities)[number]>();
  opportunities.forEach((o) => {
    if (!bestByCompany.has(o.company_id)) bestByCompany.set(o.company_id, o);
  });

  const previewOpportunity = previewId ? bestByCompany.get(previewId) ?? null : null;
  // The rest of what is open at the previewed company. Most records carry no
  // description, so without this the panel would be a title and a link; with
  // it the preview answers "what else is here", which is the question you are
  // actually asking when you point at a company.
  const previewOthers = previewId
    ? opportunities.filter((o) => o.company_id === previewId && o.id !== previewOpportunity?.id)
    : [];
  const isPreviewing = previewId !== null;
  const active = isPreviewing ? previewOpportunity : featured;
  const activeCompanyId = previewId ?? featured?.company_id ?? null;
  const activeCompany = activeCompanyId ? companyNameById.get(activeCompanyId) : undefined;
  const activeRank = active ? rankByOpportunityId.get(active.id) : undefined;

  // Which way attention moved through the ranking. Content entering from
  // below means "further down the list than what you were just looking at",
  // from above means "further up". Three pixels of direction is the whole
  // effect - it is not decoration, it is the answer to "is this better or
  // worse than what I had?" arriving before you have read the number.
  const lastRank = useRef<number | undefined>(undefined);
  const direction =
    lastRank.current === undefined || activeRank === undefined || activeRank === lastRank.current
      ? "none"
      : activeRank > lastRank.current
        ? "down"
        : "up";
  lastRank.current = activeRank;

  // Companies at the top of the scale first, then those with unread signals,
  // then everything else alphabetically. The grid is ranked, because ranking
  // is what Scout does - an alphabetical list would be an address book.
  const watch = companies
    .map((company) => ({
      company,
      lead: leadCompanyIds.has(company.id),
      featured: company.id === featured?.company_id,
      signal: unreadCompanyIds.has(company.id),
      open: openCompanyIds.has(company.id),
      openCount: openCountByCompany.get(company.id) ?? 0,
    }))
    .sort(
      (a, b) =>
        Number(b.featured) - Number(a.featured) ||
        Number(b.lead) - Number(a.lead) ||
        Number(b.signal) - Number(a.signal) ||
        Number(b.open) - Number(a.open) ||
        a.company.name.localeCompare(b.company.name),
    );


  const now = new Date();
  const dateLabel = now.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const dataPending = companiesQuery.isLoading || opportunitiesQuery.isLoading;
  const dataFailed = companiesQuery.isError || opportunitiesQuery.isError;

  return (
    <div className="dashboard-page">
      {/* The status rail is the one place the system speaks about itself. It
          is thin, it is factual, and the live dot is the only thing on the
          page that moves on its own - which is what keeps "actively
          monitoring" a statement rather than an animation. */}
      {/* While something is under inspection the rail stops describing the
          sweep and names what Scout is attending to, and the live dot stops
          pulsing and holds. A system that settles when it focuses reads as
          deliberate; one that keeps blinking reads as a screensaver. */}
      <div className={isPreviewing ? "watch-rail is-focused" : "watch-rail"}>
        <span className="watch-live">
          <span className="watch-live-dot" aria-hidden="true" />
          {isPreviewing && activeCompany
            ? `Focused on ${activeCompany}`
            : `Scout is monitoring ${companies.length} companies`}
        </span>
        <span className="watch-rail-sep" aria-hidden="true" />
        <span className="watch-rail-fact">{opportunities.length} opportunities open</span>
        {unreadCompanyCount > 0 && (
          <>
            <span className="watch-rail-sep" aria-hidden="true" />
            <span className="watch-rail-fact watch-rail-new">
              signals at {unreadCompanyCount} {unreadCompanyCount === 1 ? "company" : "companies"}
            </span>
          </>
        )}
        <time className="watch-rail-date" dateTime={now.toISOString().slice(0, 10)}>
          {dateLabel}
        </time>
      </div>

      {dataFailed ? (
        <ErrorState
          message={getErrorMessage(companiesQuery.error ?? opportunitiesQuery.error)}
        />
      ) : dataPending ? (
        <LoadingState />
      ) : !featured ? (
        <EmptyState message="Scout has not ranked any opportunities yet." />
      ) : (
        <div className="watchfloor">
          {/* --- the judgement --------------------------------------------
              Two grammars, deliberately different. At rest this is a
              sentence - a recommendation. Under preview it is a name and a
              rank - an inspection. The change in grammar is what tells you
              which mode you are in, without a label saying so. */}
          <section
            className={isPreviewing ? "verdict is-previewing" : "verdict"}
            aria-labelledby="verdict-headline"
          >
            {/* Remounting on the active company is what runs the cross-fade.
                aria-live so a screen reader is told the panel re-composed
                rather than silently changing under the user. */}
            <div
              className={hasPreviewed ? "verdict-swap has-previewed" : "verdict-swap"}
              data-direction={direction}
              key={activeCompanyId ?? "none"}
              aria-live="polite"
            >
              <p className="verdict-eyebrow">
                {isPreviewing ? (
                  activeRank ? (
                    <>
                      Ranked
                      <span className="verdict-eyebrow-count">
                        #{activeRank} of {opportunities.length}
                      </span>
                    </>
                  ) : (
                    <>Under watch</>
                  )
                ) : (
                  <>
                    Top of Scout&rsquo;s ranking
                    <span className="verdict-eyebrow-count">
                      {leadOpportunities.length} of {opportunities.length}
                    </span>
                  </>
                )}
              </p>

              <h2 id="verdict-headline" className="verdict-headline">
                {isPreviewing
                  ? activeCompany ?? "This account"
                  : `Start with ${activeCompany ?? "this account"}.`}
              </h2>

              {active ? (
                <>
                  <p className="verdict-title">{active.title}</p>

                  {firstSentence(active.description) && (
                    <p className="verdict-body">{firstSentence(active.description)}</p>
                  )}
                </>
              ) : (
                /* A company Scout watches but has nothing open on. Saying so
                   is a truthful answer; a blank panel would imply the preview
                   broke. */
                <p className="verdict-body verdict-body-quiet">
                  Scout is watching {activeCompany ?? "this company"} and has not opened an
                  opportunity here yet.
                </p>
              )}

              {/* Rendered only for a record that actually carries evidence -
                  never three zeros dressed up as reasoning. */}
              {active &&
                (active.supporting_signal_ids.length > 0 ||
                  active.capability_match_ids.length > 0 ||
                  active.recommended_services.length > 0) && (
                  <ol className="chain" aria-label="How Scout reached this">
                    <li className="chain-step">
                      <span className="chain-count">{active.supporting_signal_ids.length}</span>
                      <span className="chain-label">signals observed</span>
                    </li>
                    <li className="chain-step">
                      <span className="chain-count">{active.capability_match_ids.length}</span>
                      <span className="chain-label">capabilities matched</span>
                    </li>
                    <li className="chain-step">
                      <span className="chain-count">{active.recommended_services.length}</span>
                      <span className="chain-label">services recommended</span>
                    </li>
                  </ol>
                )}

              {previewOthers.length > 0 && (
                <ul className="verdict-others">
                  {previewOthers.map((other) => (
                    <li key={other.id}>
                      <span className="verdict-others-rank">
                        #{rankByOpportunityId.get(other.id)}
                      </span>
                      {other.title}
                    </li>
                  ))}
                </ul>
              )}

              {activeCompanyId && (
                <p className="verdict-action">
                  <Link to={`/companies/${activeCompanyId}`}>
                    Open {activeCompany ?? "company"} intelligence{" "}
                    <span aria-hidden="true">&rarr;</span>
                  </Link>
                </p>
              )}
            </div>
          </section>

          {/* --- the field ------------------------------------------------ */}
          <section className="watch" aria-labelledby="watch-heading">
            <h2 id="watch-heading" className="watch-heading">
              The watch
            </h2>

            <ul
              className={isPreviewing ? "watch-grid is-focusing" : "watch-grid"}
              onMouseLeave={() => previewCompany(null)}
            >
              {watch.map((entry, index) => (
                <li
                  key={entry.company.id}
                  className={[
                    "watch-cell",
                    entry.featured ? "is-featured" : "",
                    entry.company.id === previewId ? "is-previewing" : "",
                    entry.lead ? "is-lead" : "",
                    entry.signal ? "has-signal" : "",
                    entry.open ? "" : "is-quiet",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  // The grid resolves in rank order on arrival. Capped so a
                  // larger watch list never turns into a slow crawl.
                  style={{ animationDelay: `${Math.min(index, 24) * 26}ms` }}
                >
                  <Link
                    to={`/companies/${entry.company.id}`}
                    aria-current={entry.featured ? "true" : undefined}
                    onMouseEnter={() => previewCompany(entry.company.id)}
                    onMouseLeave={() => previewCompany(null)}
                    // Focus previews immediately - a keyboard user has already
                    // committed to the cell, so the intent delay would just be
                    // lag. Parity matters: this cannot be a mouse-only feature.
                    onFocus={() => previewCompany(entry.company.id, true)}
                    onBlur={() => previewCompany(null, true)}
                  >
                    <span className="watch-cell-name">{entry.company.name}</span>
                    {entry.openCount > 0 && (
                      <span className="watch-cell-count" aria-hidden="true">
                        {entry.openCount}
                      </span>
                    )}
                    {entry.signal && <span className="watch-cell-dot" aria-hidden="true" />}
                  </Link>
                </li>
              ))}
            </ul>

            <p className="watch-legend">
              <span className="watch-key watch-key-pick" aria-hidden="true" />
              Scout&rsquo;s pick
              <span className="watch-key watch-key-lead" aria-hidden="true" />
              top of the scale
              <span className="watch-key watch-key-signal" aria-hidden="true" />
              new signals
            </p>
          </section>
        </div>
      )}

      {/* --- the feed -----------------------------------------------------
          A live intelligence feed, not a log table. Three things carry it:

          1. A spine. The events are genuinely time-ordered, so the timeline
             is structural rather than ornamental - the node is lit while an
             item is unread and hollows out once it is not.
          2. The kind of event, named. The backend already classifies every
             notification into one of five types and the old list threw that
             away, so every row opened identically and there was nothing to
             scan by.
          3. One action per row, stated. This feed exists to get someone into
             a workflow; the recommended action is the row's point, so it sits
             at the end of the row rather than trailing the summary as grey
             text.

          Still one link per row, to the same company page as before. */}
      <section className="feed" aria-labelledby="feed-heading">
        <header className="feed-head">
          <h2 id="feed-heading" className="feed-heading">
            Intelligence feed
          </h2>
          {unreadCount > 0 && <span className="feed-count">latest {FEED_ROWS}</span>}
        </header>

        {notificationsQuery.isLoading ? (
          <LoadingState />
        ) : notificationsQuery.isError ? (
          <ErrorState message={getErrorMessage(notificationsQuery.error)} />
        ) : notifications.length === 0 ? (
          <EmptyState message="Nothing has come in yet. Scout will post here as it finds things." />
        ) : (
          <ol className="feed-list">
            {notifications.slice(0, FEED_ROWS).map((notification, index) => (
              <li
                key={notification.id}
                className={notification.is_read ? "feed-item" : "feed-item is-new"}
                style={{ animationDelay: `${Math.min(index, 8) * 45 + 500}ms` }}
              >
                <Link to={`/companies/${notification.company_id}`}>
                  <span className="feed-node" aria-hidden="true" />

                  <span className="feed-meta">
                    <span className="feed-kind">
                      {EVENT_KINDS[notification.type] ?? "Signal"}
                    </span>
                    <span className="feed-company">
                      {companyNameById.get(notification.company_id) ?? "Company"}
                    </span>
                    {relativeTime(notification.created_at) && (
                      <span className="feed-time">{relativeTime(notification.created_at)}</span>
                    )}
                  </span>

                  <span className="feed-title">
                    {notification.title.replace(REDUNDANT_PREFIX, "")}
                  </span>

                  {notification.summary && (
                    <span className="feed-summary">{notification.summary}</span>
                  )}

                  {notification.recommended_action && (
                    <span className="feed-action">
                      {notification.recommended_action}
                      <span aria-hidden="true">&rarr;</span>
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ol>
        )}
      </section>

    </div>
  );
}
