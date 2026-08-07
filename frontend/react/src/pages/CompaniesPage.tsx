// The portfolio, in Scout's order.
//
// Purpose: this page answers "which companies deserve my attention?" - and
// that answer has to come from what Scout found, not from configuration.
//
// The finding that drove the redesign: in production all 19 companies are
// monitoring-enabled and none is archived, so the status badge that used to
// be the only differentiator on each row distinguishes precisely nothing.
// Nineteen rows read as identical because on every axis the page showed,
// they were. What actually separates companies is Scout's own output - where
// their best opportunity sits in the ranking, how much is open, what
// priority it reached, and what has arrived since.
//
// Identity: the Dashboard is focus - one company, one recommendation. This
// page is comparison - the whole book at once. So its interaction is
// re-ranking: changing the lens physically moves the rows to their new
// standing, because *which companies move* is the insight a silent re-sort
// throws away.
//
// Administration (add, archive, restore, delete, Run Scout) is unchanged and
// still here - it just no longer sets the page's agenda.
import { useLayoutEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useArchiveCompany } from "../hooks/useArchiveCompany";
import { useCompanies } from "../hooks/useCompanies";
import { useConfirm } from "../hooks/useConfirm";
import { useNotifications } from "../hooks/useNotifications";
import { useExecutiveDashboard } from "../hooks/useExecutiveDashboard";
import { useOpportunityRankings } from "../hooks/useOpportunityRankings";
import { useRemoveCompany } from "../hooks/useRemoveCompany";
import { useRestoreCompany } from "../hooks/useRestoreCompany";
import { eligibleForRunScout, useRunScout } from "../hooks/useRunScout";
import { companyService } from "../services/companyService";
import type { Company } from "../types/company";
import { getErrorMessage } from "../utils/errors";

type LensId = "ranking" | "volume" | "signals" | "uncovered";

interface PortfolioRow {
  company: Company;
  openCount: number;
  bestRank: number | null;
  topPriority: number | null;
  unread: number;
}

const LENS_LABELS: Record<LensId, string> = {
  ranking: "Scout's ranking",
  volume: "Most open",
  signals: "Recent signals",
  uncovered: "No coverage",
};

// What each lens is actually claiming, in Scout's voice. Shown under the
// control so the ordering is never a mystery - a re-rankable list whose rule
// is invisible is just a list that moves.
const LENS_NOTES: Record<LensId, string> = {
  ranking: "Ordered by where each company's strongest opportunity sits in Scout's ranking.",
  volume: "Ordered by how many opportunities Scout currently has open.",
  signals: "Ordered by each company's share of the most recent signals Scout posted.",
  uncovered: "Companies Scout is watching but has not opened an opportunity on.",
};

export function CompaniesPage() {
  const [showArchived, setShowArchived] = useState(false);
  const [lens, setLens] = useState<LensId>("ranking");
  const companiesQuery = useCompanies(showArchived);
  // Two sources, deliberately. The ranking is the only thing that knows
  // *standing* (best #N of 25), but it truncates - Siemens has 7
  // opportunities and only 3 reach the top 25, and Qualcomm's 3 reach none
  // of it. Counting from it produced "Nothing open yet" for companies Scout
  // had genuinely found work at. The executive dashboard carries the
  // complete per-company set, so counts come from there and standing from
  // the ranking.
  const opportunitiesQuery = useOpportunityRankings(25);
  const executiveDashboardQuery = useExecutiveDashboard(50);
  // 100 is the endpoint's ceiling (backend/api/routers/notifications.py
  // caps `limit` at 100). Production currently has at least that many
  // unread, so any "N new signals" total this page could print would be
  // the page size wearing a number's clothes - see the rail below, which
  // counts companies instead.
  const NOTIFICATION_CEILING = 100;
  const notificationsQuery = useNotifications({ limit: NOTIFICATION_CEILING });
  const queryClient = useQueryClient();
  const archiveCompany = useArchiveCompany();
  const restoreCompany = useRestoreCompany();
  const removeCompany = useRemoveCompany();
  const { confirm, confirmDialog } = useConfirm();
  const runScout = useRunScout();

  const runnableCount = eligibleForRunScout(companiesQuery.data ?? []).length;
  const runScoutDone = runScout.results.filter(
    (r) => r.status === "refreshed" || r.status === "failed",
  ).length;

  async function handleRunScout() {
    const eligible = eligibleForRunScout(companiesQuery.data ?? []);
    const confirmed = await confirm(
      `Run Scout on ${eligible.length} ${eligible.length === 1 ? "company" : "companies"}? ` +
        "Each is refreshed in turn, which can take several minutes and uses AI credits. " +
        "Archived and monitoring-disabled companies are skipped.",
    );
    if (!confirmed) return;
    await runScout.run(eligible);
  }

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [headquarters, setHeadquarters] = useState("");
  const [website, setWebsite] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  async function handleArchive(companyId: string, companyName: string) {
    if (!(await confirm(`Archive ${companyName}? You can restore it later from the archived companies view.`))) {
      return;
    }
    setActionError(null);
    archiveCompany.mutate(companyId, { onError: (error) => setActionError(getErrorMessage(error)) });
  }

  function handleRestore(companyId: string) {
    setActionError(null);
    restoreCompany.mutate(companyId, { onError: (error) => setActionError(getErrorMessage(error)) });
  }

  async function handlePermanentlyDelete(companyId: string, companyName: string) {
    if (
      !(await confirm(
        `Permanently delete ${companyName}? This cannot be undone and removes all of its intelligence.`,
      ))
    ) {
      return;
    }
    setActionError(null);
    removeCompany.mutate(companyId, { onError: (error) => setActionError(getErrorMessage(error)) });
  }

  const createCompany = useMutation({
    mutationFn: () =>
      companyService.createCompany({
        name,
        industry: industry || undefined,
        headquarters: headquarters || undefined,
        website: website || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["companies"] });
      setName("");
      setIndustry("");
      setHeadquarters("");
      setWebsite("");
      setIsFormOpen(false);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createCompany.mutate();
  }

  // --- what Scout knows about each company ------------------------------
  const companies = companiesQuery.data ?? [];
  const opportunities = opportunitiesQuery.data ?? [];
  const notifications = notificationsQuery.data ?? [];

  const byCompany = new Map(
    (executiveDashboardQuery.data?.companies ?? []).map((c) => [c.company_id, c.opportunities]),
  );

  const rows: PortfolioRow[] = companies.map((company) => {
    const own = byCompany.get(company.id) ?? [];
    // The backend already ranks the list, so an opportunity's index *is* its
    // standing. A company's claim on your attention is its best one.
    const bestIndex = opportunities.findIndex((o) => o.company_id === company.id);
    return {
      company,
      openCount: own.length,
      bestRank: bestIndex === -1 ? null : bestIndex + 1,
      topPriority: own.reduce<number | null>(
        (best, o) => (o.priority == null ? best : Math.max(best ?? 0, o.priority)),
        null,
      ),
      unread: notifications.filter((n) => n.company_id === company.id && !n.is_read).length,
    };
  });

  // A lens earns its place only if it can actually separate the portfolio.
  // With every company on zero unread signals, "New signals" would be a
  // control that reorders nothing - so it is not rendered. Same test for
  // "No coverage": if Scout has found something everywhere, there is no
  // gap to show. This is a runtime check rather than a judgement baked in
  // from one look at the data, so the page stays honest as the data moves.
  const companiesWithSignals = rows.filter((r) => r.unread > 0).length;
  // When the fetch comes back full, per-company counts are lower bounds
  // rather than totals, and the row renders "6+" instead of "6".
  const signalsSaturated = notifications.length >= NOTIFICATION_CEILING;
  const uncoveredCount = rows.filter((r) => !r.company.archived_at && r.openCount === 0).length;
  const availableLenses: LensId[] = [
    "ranking",
    "volume",
    ...(companiesWithSignals > 1 ? (["signals"] as LensId[]) : []),
    ...(uncoveredCount > 0 ? (["uncovered"] as LensId[]) : []),
  ];
  const activeLens = availableLenses.includes(lens) ? lens : "ranking";

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const searched = normalizedSearch
    ? rows.filter(
        (r) =>
          r.company.name.toLowerCase().includes(normalizedSearch) ||
          (r.company.industry ?? "").toLowerCase().includes(normalizedSearch),
      )
    : rows;

  const lensed =
    activeLens === "uncovered" ? searched.filter((r) => r.openCount === 0) : searched;

  const ordered = [...lensed].sort((a, b) => {
    // Archived companies always sink: they are not competing for attention.
    if (!!a.company.archived_at !== !!b.company.archived_at) {
      return a.company.archived_at ? 1 : -1;
    }
    if (activeLens === "volume") {
      if (b.openCount !== a.openCount) return b.openCount - a.openCount;
    } else if (activeLens === "signals") {
      if (b.unread !== a.unread) return b.unread - a.unread;
    }
    // Every lens falls back to Scout's ranking, so ties never reorder
    // arbitrarily between renders. A company with nothing open sorts last.
    const ar = a.bestRank ?? Number.MAX_SAFE_INTEGER;
    const br = b.bestRank ?? Number.MAX_SAFE_INTEGER;
    if (ar !== br) return ar - br;
    return a.company.name.localeCompare(b.company.name);
  });

  // --- the rows travel to their new standing ----------------------------
  // FLIP: measure where each row is, let React reorder, then animate each
  // row from where it *was* to where it now is. The movement is the point -
  // seeing a company climb eight places when the question changes is the
  // insight a silent re-sort throws away. Transform only, so it never
  // triggers layout, and one-shot.
  const rowRefs = useRef(new Map<string, HTMLLIElement>());
  const previousRects = useRef(new Map<string, DOMRect>());
  const previousLens = useRef(activeLens);

  useLayoutEffect(() => {
    const lensChanged = previousLens.current !== activeLens;
    previousLens.current = activeLens;

    if (lensChanged && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      rowRefs.current.forEach((node, id) => {
        const before = previousRects.current.get(id);
        if (!before) return;
        const after = node.getBoundingClientRect();
        const dy = before.top - after.top;
        if (Math.abs(dy) < 1) return;

        // A row that genuinely travels 1000px reads as a projectile, not a
        // transition - and at this speed the eye cannot follow it anyway.
        // Long moves are clamped and fade in instead, so a row crossing the
        // whole list still says "I came from far away" without flying.
        const CLAMP = 280;
        const clamped = Math.max(-CLAMP, Math.min(CLAMP, dy));
        const isLongMove = Math.abs(dy) > CLAMP;
        node.animate(
          [
            { transform: `translateY(${clamped}px)`, opacity: isLongMove ? 0.35 : 1 },
            { transform: "translateY(0)", opacity: 1 },
          ],
          {
            // Longer moves get a touch more time, so distance still reads as
            // distance rather than everything resolving in the same beat.
            duration: isLongMove ? 320 : 260,
            easing: "cubic-bezier(0.16, 1, 0.3, 1)",
          },
        );
      });
    }

    previousRects.current = new Map(
      [...rowRefs.current].map(([id, node]) => [id, node.getBoundingClientRect()]),
    );
  }, [activeLens, ordered.length, searchTerm]);

  const isLoading =
    companiesQuery.isLoading || opportunitiesQuery.isLoading || executiveDashboardQuery.isLoading;
  const openTotal = rows.reduce((n, r) => n + r.openCount, 0);
  const activeCount = rows.filter((r) => !r.company.archived_at).length;

  return (
    <div className="companies-page portfolio">
      {confirmDialog && <ConfirmDialog {...confirmDialog} />}

      {/* Scout's read on the whole book, in the same register as the
          Dashboard's status rail - factual, caption-scale, no ornament. */}
      <div className="portfolio-rail">
        <span className="portfolio-rail-lead">
          <span className="portfolio-rail-dot" aria-hidden="true" />
          {isLoading
            ? "Scout is reading the portfolio"
            : `Scout has ranked ${activeCount} ${activeCount === 1 ? "company" : "companies"}`}
        </span>
        {!isLoading && (
          <>
            <span className="portfolio-rail-sep" aria-hidden="true" />
            <span>{openTotal} opportunities open</span>
          </>
        )}
        {!isLoading && companiesWithSignals > 0 && (
          <>
            <span className="portfolio-rail-sep" aria-hidden="true" />
            {/* Companies, not signals. The signal total is unknowable from
                a capped list, and "how many accounts are talking" is the
                portfolio-level fact anyway. */}
            <span className="portfolio-rail-new">
              signals at {companiesWithSignals} of {activeCount}
            </span>
          </>
        )}
      </div>

      <header className="portfolio-head">
        <div>
          <h1 className="portfolio-title">Portfolio</h1>
          <p className="portfolio-subtitle">{LENS_NOTES[activeLens]}</p>
        </div>
        <div className="portfolio-admin">
          <button type="button" onClick={() => setIsFormOpen((open) => !open)}>
            {isFormOpen ? "Cancel" : "Add company"}
          </button>
          <button
            type="button"
            className="primary-button run-scout-button"
            onClick={handleRunScout}
            disabled={runScout.isRunning || runnableCount === 0}
          >
            {runScout.isRunning ? "Running Scout…" : `Run Scout (${runnableCount})`}
          </button>
        </div>
      </header>

      {/* The lens control. Each option is a question about the portfolio,
          and switching moves the rows rather than redrawing the list. */}
      <div className="portfolio-controls">
        <div className="lens-group" role="group" aria-label="Order the portfolio by">
          {availableLenses.map((id) => (
            <button
              key={id}
              type="button"
              className={id === activeLens ? "lens is-active" : "lens"}
              aria-pressed={id === activeLens}
              onClick={() => setLens(id)}
            >
              {LENS_LABELS[id]}
            </button>
          ))}
        </div>
        <input
          type="search"
          className="portfolio-search"
          placeholder="Filter by name or industry…"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          aria-label="Filter companies"
        />
        <label className="portfolio-archived">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => setShowArchived(event.target.checked)}
          />
          Archived
        </label>
      </div>

      {(runScout.isRunning || runScout.summary) && (
        <section className="run-scout-panel" aria-label="Run Scout progress">
          <div className="run-scout-progress">
            <progress value={runScoutDone} max={runScout.results.length || 1} />
            <span>
              {runScoutDone} of {runScout.results.length} companies
            </span>
            {runScout.isRunning && (
              <button type="button" onClick={runScout.cancel}>
                Cancel
              </button>
            )}
          </div>
          {runScout.summary && (
            <p className="run-scout-summary">
              {runScout.summary.cancelled ? "Cancelled after " : "Finished: "}
              {runScout.summary.refreshed} refreshed
              {runScout.summary.failed > 0 && `, ${runScout.summary.failed} failed`} in{" "}
              {Math.round(runScout.summary.elapsedMs / 1000)}s.
            </p>
          )}
          <ul className="run-scout-list">
            {runScout.results.map((result) => (
              <li key={result.companyId} className={`is-${result.status}`}>
                <span>{result.name}</span>
                <span className="run-scout-status">{result.status}</span>
                {result.detail && <small className="run-scout-detail">{result.detail}</small>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {isFormOpen && (
        <section className="portfolio-form" aria-label="Add a company">
          <form onSubmit={handleSubmit} className="add-company-form">
            <label htmlFor="company-name">Name</label>
            <input id="company-name" value={name} onChange={(event) => setName(event.target.value)} required />
            <label htmlFor="company-industry">Industry</label>
            <input id="company-industry" value={industry} onChange={(event) => setIndustry(event.target.value)} />
            <label htmlFor="company-hq">Headquarters</label>
            <input id="company-hq" value={headquarters} onChange={(event) => setHeadquarters(event.target.value)} />
            <label htmlFor="company-website">Website</label>
            <input id="company-website" value={website} onChange={(event) => setWebsite(event.target.value)} />
            {createCompany.isError && <p className="form-error">{getErrorMessage(createCompany.error)}</p>}
            <button type="submit" className="primary-button" disabled={createCompany.isPending}>
              {createCompany.isPending ? "Adding…" : "Add company"}
            </button>
          </form>
        </section>
      )}

      {actionError && <p className="form-error">{actionError}</p>}

      {isLoading ? (
        <LoadingState />
      ) : companiesQuery.isError ? (
        <ErrorState message={getErrorMessage(companiesQuery.error)} />
      ) : companies.length === 0 ? (
        <EmptyState message="No companies yet. Add one and Scout will start watching it." />
      ) : ordered.length === 0 ? (
        <EmptyState message={`Nothing matches "${searchTerm}".`} />
      ) : (
        <ol className="portfolio-list">
          {ordered.map((row, index) => (
            <li
              key={row.company.id}
              ref={(node) => {
                if (node) rowRefs.current.set(row.company.id, node);
                else rowRefs.current.delete(row.company.id);
              }}
              className={[
                "portfolio-row",
                row.company.archived_at ? "is-archived" : "",
                row.openCount === 0 ? "is-uncovered" : "",
                row.unread > 0 ? "has-signals" : "",
                row.topPriority === 10 ? "is-lead" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {/* Standing under the current lens, not a database id. It is
                  the first thing on the row because it is the answer to the
                  page's question. */}
              <span className="portfolio-rank" aria-hidden="true">
                {index + 1}
              </span>

              <Link to={`/companies/${row.company.id}`} className="portfolio-link">
                <span className="portfolio-name">{row.company.name}</span>
                {row.company.industry && (
                  <span className="portfolio-industry">{row.company.industry}</span>
                )}

                {/* The justification for the placement, on the row. */}
                <span className="portfolio-facts">
                  {row.company.archived_at ? (
                    <span className="portfolio-fact is-quiet">Archived</span>
                  ) : row.openCount === 0 ? (
                    <span className="portfolio-fact is-quiet">Nothing open yet</span>
                  ) : (
                    <>
                      <span className="portfolio-fact">
                        {row.openCount} open
                      </span>
                      {row.bestRank !== null && row.bestRank !== index + 1 && (
                        <span className="portfolio-fact">best #{row.bestRank}</span>
                      )}
                      {row.topPriority === 10 && (
                        <span className="portfolio-fact is-lead">top of scale</span>
                      )}
                    </>
                  )}
                  {row.unread > 0 && (
                    <span className="portfolio-fact is-signal">
                      <span className="portfolio-signal-dot" aria-hidden="true" />
                      {row.unread}
                      {signalsSaturated ? "+" : ""} new
                    </span>
                  )}
                </span>
              </Link>

              {/* Administration lives on the row but not in the reading
                  order - revealed on hover or keyboard focus, because it is
                  not what the page is for. */}
              <span className="portfolio-actions">
                {row.company.archived_at ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleRestore(row.company.id)}
                      disabled={restoreCompany.isPending}
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => handlePermanentlyDelete(row.company.id, row.company.name)}
                      disabled={removeCompany.isPending}
                    >
                      Delete
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleArchive(row.company.id, row.company.name)}
                    disabled={archiveCompany.isPending}
                  >
                    Archive
                  </button>
                )}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
