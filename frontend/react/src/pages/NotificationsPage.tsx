// Notifications - the observation record.
//
// The Dashboard's feed shows the newest handful and asks "what should I
// do". This page is the archive, and its question is different: what has
// Scout observed, and what does it add up to?
//
// The production data has a shape a flat reverse-chronological list
// throws away. Every observation in the window belongs to a contiguous
// per-company run: sorted by time, the company changes exactly as many
// times as there are companies (verified against production - 16 runs for
// 16 companies, no interleaving), because Scout works through the
// portfolio one account at a time. So an observation is not an isolated
// ping; it is one facet of one account's pass. The page renders that pass
// as a spine, each company a stop on it in the order Scout reached them.
//
// Selecting a kind thins the spine rather than reordering it - the
// chronology is the point, and re-ranking accounts is the Companies
// page's job, not this one's.
//
// Two things the data does not support, and which are therefore not
// implied anywhere here:
//   - recommended_action is a pure function of type (all 32
//     opportunity_alert rows say "Review opportunity"), so it is shown
//     once per kind in the legend rather than repeated on every row as
//     if Scout had reasoned about each one. It is derived from the data
//     rather than hardcoded, so it stays honest if the backend changes.
//   - the endpoint caps limit at 100 with no offset, so this is the most
//     recent 100 observations, never provably all of them. The header
//     says so when the cap is hit.
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useCompanies } from "../hooks/useCompanies";
import { useMarkNotificationRead } from "../hooks/useMarkNotificationRead";
import { useNotifications } from "../hooks/useNotifications";
import { useToasts } from "../hooks/useToasts";
import { getErrorMessage } from "../utils/errors";
import type { Notification } from "../types/notification";

// The endpoint's ceiling. Asking for more is a 422.
const PAGE_LIMIT = 100;

// Display names for the five kinds the notification service emits. The
// recommended action is not listed here on purpose - it comes from the
// data.
const KIND_LABEL: Record<string, string> = {
  opportunity_alert: "Opportunity",
  strategic_initiative: "Strategic move",
  ai_initiative: "AI initiative",
  hiring_spike: "Hiring",
  leadership_change: "Leadership",
};

// Every opportunity title starts with this; the kind is already on the
// chip beside it, so the prefix is pure repetition. Same treatment as the
// Dashboard feed.
const REDUNDANT_PREFIX = /^New high-confidence opportunity:\s*/i;

interface Stop {
  companyId: string;
  companyName: string;
  at: string;
  items: Notification[];
  kindCounts: Map<string, number>;
}

function kindLabel(kind: string): string {
  return KIND_LABEL[kind] ?? kind.replace(/_/g, " ");
}

function formatClock(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function formatDay(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function formatSpan(fromIso: string, toIso: string): string {
  const minutes = Math.round((new Date(toIso).getTime() - new Date(fromIso).getTime()) / 60000);
  if (minutes < 60) {
    return `${minutes} minutes`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} hours` : `${hours}h ${rest}m`;
}

export function NotificationsPage() {
  const [kind, setKind] = useState<string | null>(null);
  const [hideReviewed, setHideReviewed] = useState(false);

  const notificationsQuery = useNotifications({ limit: PAGE_LIMIT });
  const companiesQuery = useCompanies();
  const markRead = useMarkNotificationRead();
  const { toasts, pushToast, dismissToast } = useToasts();

  const notifications = useMemo(() => notificationsQuery.data ?? [], [notificationsQuery.data]);

  const companyNames = useMemo(() => {
    const names = new Map<string, string>();
    for (const company of companiesQuery.data ?? []) {
      names.set(company.id, company.name);
    }
    return names;
  }, [companiesQuery.data]);

  // Oldest first: the spine reads in the order Scout worked, not in the
  // order the API happened to return.
  const chronological = useMemo(
    () => [...notifications].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [notifications],
  );

  const kindCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of notifications) {
      counts.set(item.type, (counts.get(item.type) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [notifications]);

  // Derived, not assumed: a kind only advertises an action when every
  // observation of that kind carries the same one.
  const actionByKind = useMemo(() => {
    const seen = new Map<string, Set<string>>();
    for (const item of notifications) {
      if (!item.recommended_action) {
        continue;
      }
      const set = seen.get(item.type) ?? new Set<string>();
      set.add(item.recommended_action);
      seen.set(item.type, set);
    }
    const single = new Map<string, string>();
    for (const [type, actions] of seen) {
      if (actions.size === 1) {
        single.set(type, [...actions][0]);
      }
    }
    return single;
  }, [notifications]);

  // Consecutive runs of the same company become the stops on the spine.
  const stops = useMemo<Stop[]>(() => {
    const result: Stop[] = [];
    for (const item of chronological) {
      const last = result[result.length - 1];
      if (last && last.companyId === item.company_id) {
        last.items.push(item);
        last.kindCounts.set(item.type, (last.kindCounts.get(item.type) ?? 0) + 1);
        continue;
      }
      result.push({
        companyId: item.company_id,
        companyName: companyNames.get(item.company_id) ?? "Unknown company",
        at: item.created_at,
        items: [item],
        kindCounts: new Map([[item.type, 1]]),
      });
    }
    return result;
  }, [chronological, companyNames]);

  // Filtering thins each stop; a stop with nothing left drops off the
  // spine rather than rearranging the ones that remain.
  const visibleStops = useMemo(
    () =>
      stops
        .map((stop) => ({
          ...stop,
          items: stop.items.filter(
            (item) => (kind === null || item.type === kind) && (!hideReviewed || !item.is_read),
          ),
        }))
        .filter((stop) => stop.items.length > 0),
    [stops, kind, hideReviewed],
  );

  const visibleCount = visibleStops.reduce((total, stop) => total + stop.items.length, 0);
  const reviewedCount = notifications.filter((item) => item.is_read).length;
  const atCap = notifications.length >= PAGE_LIMIT;

  // Companies Scout is monitoring that produced nothing in this window -
  // itself worth knowing, and invisible in a flat list.
  const quietCompanies = useMemo(() => {
    const observed = new Set(notifications.map((item) => item.company_id));
    return (companiesQuery.data ?? [])
      .filter((company) => !observed.has(company.id) && !company.archived_at)
      .map((company) => company.name);
  }, [notifications, companiesQuery.data]);

  function handleMarkRead(notificationId: string) {
    markRead.mutate(notificationId, {
      onError: (error) => pushToast(getErrorMessage(error), "error"),
    });
  }

  // Triage happens per account - you read what Scout found at one company
  // and clear the lot - so the stop carries the bulk action and the rows
  // only need it for the odd exception.
  function handleMarkStopRead(stop: Stop) {
    const unread = stop.items.filter((item) => !item.is_read);
    for (const item of unread) {
      markRead.mutate(item.id, {
        onError: (error) => pushToast(getErrorMessage(error), "error"),
      });
    }
  }

  const isLoading = notificationsQuery.isLoading || companiesQuery.isLoading;

  return (
    <div className="observations">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <header className="obs-head">
        <p className="obs-eyebrow">The observation record</p>
        <h1>What Scout has observed</h1>

        {notificationsQuery.isError ? (
          <ErrorState message={getErrorMessage(notificationsQuery.error)} />
        ) : isLoading ? (
          <p className="obs-lede obs-lede-waiting">Reading the record&hellip;</p>
        ) : notifications.length === 0 ? (
          <p className="obs-lede">Scout has not recorded any observations yet.</p>
        ) : (
          <>
            <p className="obs-lede">
              Scout worked through {stops.length} of your {companyNames.size} companies one account at a time,
              recording {notifications.length} observations over{" "}
              {formatSpan(chronological[0].created_at, chronological[chronological.length - 1].created_at)} on{" "}
              {formatDay(chronological[0].created_at)}.
            </p>
            {atCap && (
              <p className="obs-caveat">
                Showing the {PAGE_LIMIT} most recent. The notifications endpoint returns at most {PAGE_LIMIT} and
                has no paging, so anything older is not reachable from here.
              </p>
            )}
          </>
        )}
      </header>

      {!isLoading && notifications.length > 0 && (
        <>
          {/* --- the lens -------------------------------------------------- */}
          <div className="obs-lens">
            <div className="obs-kinds" role="group" aria-label="Filter by kind of observation">
              <button
                type="button"
                className={`obs-kind${kind === null ? " active" : ""}`}
                aria-pressed={kind === null}
                onClick={() => setKind(null)}
              >
                <span className="obs-kind-label">Everything</span>
                <span className="obs-kind-count">{notifications.length}</span>
              </button>
              {kindCounts.map(([type, count]) => (
                <button
                  key={type}
                  type="button"
                  className={`obs-kind kind-${type}${kind === type ? " active" : ""}`}
                  aria-pressed={kind === type}
                  onClick={() => setKind(kind === type ? null : type)}
                >
                  <span className="obs-kind-dot" />
                  <span className="obs-kind-label">{kindLabel(type)}</span>
                  <span className="obs-kind-count">{count}</span>
                </button>
              ))}
            </div>

            <label className="obs-toggle">
              <input
                type="checkbox"
                checked={hideReviewed}
                onChange={(event) => setHideReviewed(event.target.checked)}
              />
              Hide reviewed
              <span className="obs-toggle-count">
                {reviewedCount} of {notifications.length}
              </span>
            </label>
          </div>

          {/* The action attached to a kind is the same for every observation
              of that kind, so it belongs to the kind, not to the item. */}
          {kind !== null && actionByKind.has(kind) && (
            <p className="obs-kind-action">
              Scout routes every {kindLabel(kind).toLowerCase()} observation the same way:{" "}
              <strong>{actionByKind.get(kind)}</strong>.
            </p>
          )}

          {/* --- the sweep ------------------------------------------------- */}
          {visibleStops.length === 0 ? (
            <EmptyState message="Nothing matches these filters." />
          ) : (
            <ol className="sweep">
              {visibleStops.map((stop) => (
                <li key={`${stop.companyId}-${stop.at}`} className="sweep-stop">
                  <div className="sweep-marker" aria-hidden="true" />

                  <div className="sweep-when">
                    <span className="sweep-time">{formatClock(stop.at)}</span>
                    <span className="sweep-day">{formatDay(stop.at)}</span>
                  </div>

                  <div className="sweep-body">
                    <div className="sweep-stop-head">
                      <Link to={`/companies/${stop.companyId}`} className="sweep-company">
                        {stop.companyName}
                      </Link>
                      <span className="sweep-tally">
                        {stop.items.length} observation{stop.items.length === 1 ? "" : "s"}
                      </span>
                      {kind === null && (
                        <span className="sweep-mix" aria-hidden="true">
                          {[...stop.kindCounts.entries()].map(([type, count]) => (
                            <span key={type} className={`sweep-mix-dot kind-${type}`} title={kindLabel(type)}>
                              {count > 1 && <span className="sweep-mix-count">{count}</span>}
                            </span>
                          ))}
                        </span>
                      )}
                      {stop.items.some((item) => !item.is_read) && (
                        <button
                          type="button"
                          className="sweep-clear"
                          onClick={() => handleMarkStopRead(stop)}
                          disabled={markRead.isPending}
                        >
                          Mark all reviewed
                        </button>
                      )}
                    </div>

                    <ul className="obs-list">
                      {stop.items.map((item) => (
                        <li key={item.id} className={`obs-item${item.is_read ? " reviewed" : ""}`}>
                          <div className="obs-item-head">
                            <span className={`obs-tag kind-${item.type}`}>{kindLabel(item.type)}</span>
                            <p className="obs-title">{item.title.replace(REDUNDANT_PREFIX, "")}</p>
                          </div>
                          {item.summary && <p className="obs-summary">{item.summary}</p>}
                          {item.is_read ? (
                            <span className="obs-reviewed">Reviewed</span>
                          ) : (
                            <button
                              type="button"
                              className="obs-review"
                              onClick={() => handleMarkRead(item.id)}
                              disabled={markRead.isPending}
                            >
                              Mark reviewed
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                </li>
              ))}
            </ol>
          )}

          <p className="obs-foot">
            {kind === null
              ? `${visibleCount} observations across ${visibleStops.length} accounts.`
              : `${visibleCount} ${kindLabel(kind).toLowerCase()} observation${
                  visibleCount === 1 ? "" : "s"
                } across ${visibleStops.length} account${visibleStops.length === 1 ? "" : "s"}.`}
          </p>

          {quietCompanies.length > 0 && (
            <p className="obs-quiet">
              Scout recorded nothing for {quietCompanies.join(", ")} in this window.
            </p>
          )}
        </>
      )}

      {isLoading && <LoadingState />}
    </div>
  );
}
