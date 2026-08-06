// The demand map.
//
// Purpose. The other three pages are all account-centric and each already
// answers its own question well: the Dashboard says what to do, Companies
// says which account deserves attention, Company Intelligence says why Scout
// believes something about one account. This page used to be a fourth
// account-centric view - opportunities grouped by company, with the same
// reasoning the Company Intelligence thread now shows in more depth - which
// after those redesigns left it with nothing of its own to say.
//
// The axis nobody else uses is capability. Every other page reads
// account -> work. This one reads work -> accounts: what kind of business is
// Scout actually finding, and where is the demand concentrated? That is a
// practice question rather than a seller's question, and it is the only
// question here that no other page answers.
//
// The production data supports it: 50 opportunities carry 9 distinct
// services, and the spread is real rather than uniform - AI/ML appears in 20
// opportunities across 12 companies while four services appear once or twice.
// Depth and breadth genuinely differ per service (IoT is 11 opportunities but
// only 6 companies), which is exactly the distinction a practice lead needs
// and a flat count would hide.
//
// The signature interaction is the inversion itself: choose a service and the
// same ranked instrument re-measures, showing the accounts asking for it.
import { useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useExecutiveDashboard } from "../hooks/useExecutiveDashboard";
import { useToasts } from "../hooks/useToasts";
import { meetingBriefService } from "../services/meetingBriefService";
import { outreachDraftService } from "../services/outreachDraftService";
import { v3ReportService } from "../services/v3ReportService";
import { getErrorMessage } from "../utils/errors";

type ActionType = "meeting_brief" | "outreach_draft" | "report";

const ACTION_LABELS: Record<ActionType, string> = {
  meeting_brief: "Meeting brief",
  outreach_draft: "Outreach draft",
  report: "Report",
};

interface ServiceDemand {
  service: string;
  opportunities: number;
  companies: number;
  topPriority: number;
  // Opportunities per company. The distinction between a service wanted a
  // little by many and a lot by few is the one a flat count destroys.
  depth: number;
}

interface AccountDemand {
  companyId: string;
  companyName: string;
  opportunities: { id: string; title: string; priority: number | null }[];
}

export function AnalyticsPage() {
  const dashboardQuery = useExecutiveDashboard(50);
  const companies = dashboardQuery.data?.companies ?? [];
  const { toasts, pushToast, dismissToast } = useToasts();
  const [triggeringAction, setTriggeringAction] = useState<string | null>(null);
  const [focusedService, setFocusedService] = useState<string | null>(null);

  async function handleAction(companyId: string, actionType: ActionType) {
    const actionKey = `${companyId}-${actionType}`;
    setTriggeringAction(actionKey);
    try {
      if (actionType === "meeting_brief") {
        await meetingBriefService.generate(companyId);
      } else if (actionType === "outreach_draft") {
        await outreachDraftService.generate({ companyId, outreachType: "Email", talkingPoints: [] });
      } else {
        await v3ReportService.generate(companyId);
      }
      pushToast(`${ACTION_LABELS[actionType]} started - open the company page to watch it finish.`, "success");
    } catch (error) {
      pushToast(getErrorMessage(error), "error");
    } finally {
      setTriggeringAction(null);
    }
  }

  // --- the map ------------------------------------------------------------
  const flat = companies.flatMap((c) =>
    c.opportunities.map((o) => ({ companyId: c.company_id, companyName: c.company_name, ...o })),
  );

  const demandByService = new Map<string, { opps: typeof flat; companies: Set<string> }>();
  flat.forEach((o) => {
    o.recommended_services.forEach((service) => {
      const entry = demandByService.get(service) ?? { opps: [], companies: new Set<string>() };
      entry.opps.push(o);
      entry.companies.add(o.companyId);
      demandByService.set(service, entry);
    });
  });

  const demand: ServiceDemand[] = [...demandByService.entries()]
    .map(([service, entry]) => ({
      service,
      opportunities: entry.opps.length,
      companies: entry.companies.size,
      topPriority: entry.opps.reduce((best, o) => Math.max(best, o.priority ?? 0), 0),
      depth: entry.opps.length / entry.companies.size,
    }))
    .sort((a, b) => b.opportunities - a.opportunities);

  const peak = demand[0]?.opportunities ?? 1;
  const quiet = demand.filter((d) => d.opportunities <= 2);
  const live = demand.filter((d) => d.opportunities > 2);

  // --- what Scout is seeing ----------------------------------------------
  // Observations, derived rather than written down. Every claim below is
  // computed from the same data the map draws, so it stays true as the
  // portfolio moves - a hardcoded "AI and cloud dominate" would quietly
  // become a lie the first time it stopped being one.
  const topTwo = demand.slice(0, 2).map((d) => d.service);
  const involvingTopTwo = flat.filter((o) =>
    o.recommended_services.some((svc) => topTwo.includes(svc)),
  ).length;
  const topTwoShare = flat.length > 0 ? Math.round((involvingTopTwo / flat.length) * 100) : 0;

  // Which capabilities keep being needed together. Scout is not asked to
  // pair them - the pairing falls out of what it finds, which is what makes
  // it an observation rather than a configuration.
  const pairCounts = new Map<string, number>();
  flat.forEach((o) => {
    const svcs = [...new Set(o.recommended_services)].sort();
    for (let i = 0; i < svcs.length; i += 1) {
      for (let j = i + 1; j < svcs.length; j += 1) {
        const key = `${svcs[i]}||${svcs[j]}`;
        pairCounts.set(key, (pairCounts.get(key) ?? 0) + 1);
      }
    }
  });
  const topPair = [...pairCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  const multiServiceCount = flat.filter((o) => o.recommended_services.length > 1).length;

  // The evidence mix per service, and the portfolio's own baseline, so the
  // page can point at a service that is being found differently from the
  // rest rather than just reporting four numbers.
  const evidenceByService = new Map<string, Record<string, number>>();
  flat.forEach((o) =>
    o.recommended_services.forEach((svc) => {
      const mix = evidenceByService.get(svc) ?? {};
      Object.entries(o.signal_type_counts ?? {}).forEach(([type, n]) => {
        mix[type] = (mix[type] ?? 0) + n;
      });
      evidenceByService.set(svc, mix);
    }),
  );
  const portfolioMix: Record<string, number> = {};
  flat.forEach((o) =>
    Object.entries(o.signal_type_counts ?? {}).forEach(([type, n]) => {
      portfolioMix[type] = (portfolioMix[type] ?? 0) + n;
    }),
  );
  const portfolioTotal = Object.values(portfolioMix).reduce((a, b) => a + b, 0) || 1;

  function shareOf(mix: Record<string, number>, type: string): number {
    const total = Object.values(mix).reduce((a, b) => a + b, 0);
    return total === 0 ? 0 : mix[type] / total;
  }

  // The service line Scout is finding by a different route from everything
  // else - the biggest positive deviation from the portfolio's own mix.
  const anomaly = demand
    .filter((d) => d.opportunities > 2)
    .map((d) => {
      const mix = evidenceByService.get(d.service) ?? {};
      let best: { type: string; delta: number } | null = null;
      Object.keys(portfolioMix).forEach((type) => {
        const delta = shareOf(mix, type) - portfolioMix[type] / portfolioTotal;
        if (!best || delta > best.delta) best = { type, delta };
      });
      const chosen = best ?? { type: "", delta: 0 };
      const mixOfService = evidenceByService.get(d.service) ?? {};
      return {
        service: d.service,
        ...chosen,
        // The share itself, and the book's baseline, so the observation can
        // quote a figure like every other line rather than a glyph.
        share: Math.round(shareOf(mixOfService, chosen.type) * 100),
        baseline: Math.round(((portfolioMix[chosen.type] ?? 0) / portfolioTotal) * 100),
      };
    })
    .sort((a, b) => b.delta - a.delta)[0];

  // The accounts asking for whatever service is in focus - the inverted view.
  const focusedAccounts: AccountDemand[] = focusedService
    ? [
        ...flat
          .filter((o) => o.recommended_services.includes(focusedService))
          .reduce((map, o) => {
            const entry = map.get(o.companyId) ?? {
              companyId: o.companyId,
              companyName: o.companyName,
              opportunities: [],
            };
            entry.opportunities.push({ id: o.id, title: o.title, priority: o.priority });
            map.set(o.companyId, entry);
            return map;
          }, new Map<string, AccountDemand>())
          .values(),
      ].sort((a, b) => b.opportunities.length - a.opportunities.length)
    : [];

  const accountPeak = focusedAccounts[0]?.opportunities.length ?? 1;

  // --- the instrument re-measures -----------------------------------------
  // Bars animate their own width when the subject changes, rather than the
  // list being replaced. That is the whole point of the interaction: it is
  // the same instrument reading a different axis, so the measurement should
  // visibly re-take rather than the panel swapping out.
  const barRefs = useRef(new Map<string, HTMLSpanElement>());
  const previousWidths = useRef(new Map<string, number>());

  useLayoutEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    barRefs.current.forEach((node, key) => {
      const target = node.getBoundingClientRect().width;
      const before = previousWidths.current.get(key);
      if (before === undefined || Math.abs(before - target) < 1 || target === 0) return;
      node.animate([{ width: `${before}px` }, { width: `${target}px` }], {
        duration: 340,
        easing: "cubic-bezier(0.16, 1, 0.3, 1)",
      });
    });
    previousWidths.current = new Map(
      [...barRefs.current].map(([key, node]) => [key, node.getBoundingClientRect().width]),
    );
  }, [focusedService, demand.length, focusedAccounts.length]);

  const totalOpportunities = flat.length;

  return (
    <div className="analytics-page demandmap">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className="demand-rail">
        <span className="demand-rail-lead">
          <span className="demand-rail-dot" aria-hidden="true" />
          {dashboardQuery.isLoading
            ? "Scout is mapping demand"
            : `${totalOpportunities} opportunities across ${companies.length} companies`}
        </span>
        {!dashboardQuery.isLoading && demand.length > 0 && (
          <>
            <span className="demand-rail-sep" aria-hidden="true" />
            <span>{demand.length} service lines in play</span>
          </>
        )}
      </div>

      <header className="demand-head">
        <h1 className="demand-title">{focusedService ?? "What Scout is seeing"}</h1>
        <p className="demand-subtitle">
          {focusedService
            ? "How this capability behaves across the portfolio - what it is usually needed alongside, how Scout detects it, and who is asking."
            : "Patterns across the whole portfolio - what kind of work keeps coming up, what it travels with, and how Scout is finding it."}
        </p>
        {focusedService && (
          <button type="button" className="demand-back" onClick={() => setFocusedService(null)}>
            <span aria-hidden="true">&larr;</span> All service lines
          </button>
        )}
      </header>

      {/* Scout's observations. The map below is the evidence for them, not
          the point - a page of bars is a report, and a report is not what
          anyone opens an intelligence product to read. Each statement is
          computed from the same data the bars draw. */}
      {!dashboardQuery.isLoading && !focusedService && demand.length > 1 && (
        <ul className="observations">
          <li>
            <span className="observation-figure">{topTwoShare}%</span>
            <span className="observation-text">
              of everything Scout has found runs through just two of {demand.length} service
              lines &mdash; {topTwo[0]} and {topTwo[1]}.
            </span>
          </li>
          {topPair && multiServiceCount > 0 && (
            <li>
              <span className="observation-figure">{multiServiceCount}</span>
              <span className="observation-text">
                of {flat.length} opportunities need more than one capability. The pairing Scout
                keeps finding is {topPair[0].split("||")[0]} with {topPair[0].split("||")[1]},
                together {topPair[1]} times.
              </span>
            </li>
          )}
          {anomaly && anomaly.delta > 0.08 && (
            <li>
              <span className="observation-figure">{anomaly.share}%</span>
              <span className="observation-text">
                of the evidence behind {anomaly.service} is {anomaly.type} signals, against{" "}
                {anomaly.baseline}% across the book &mdash; Scout is finding this one by a
                different route from everything else.
              </span>
            </li>
          )}
          {quiet.length > 0 && (
            <li>
              <span className="observation-figure">{quiet.length}</span>
              <span className="observation-text">
                service lines have produced almost nothing across all {companies.length} companies.
              </span>
            </li>
          )}
        </ul>
      )}

      {dashboardQuery.isLoading ? (
        <LoadingState />
      ) : dashboardQuery.isError ? (
        <ErrorState message={getErrorMessage(dashboardQuery.error)} />
      ) : demand.length === 0 ? (
        <EmptyState message="Scout has not recommended any services yet." />
      ) : focusedService ? (
        /* --- inverted: how one capability behaves across the book -------- */
        <>
          {(() => {
            const mix = evidenceByService.get(focusedService) ?? {};
            const mixTotal = Object.values(mix).reduce((a, b) => a + b, 0);
            const travelsWith = [...pairCounts.entries()]
              .filter(([key]) => key.split("||").includes(focusedService))
              .map(([key, n]) => ({
                other: key.split("||").find((x) => x !== focusedService) ?? "",
                count: n,
              }))
              .sort((a, b) => b.count - a.count);

            return (
              <div className="pattern-grid">
                <section className="pattern-block">
                  <h2 className="pattern-label">Usually needed alongside</h2>
                  {travelsWith.length === 0 ? (
                    <p className="pattern-empty">
                      Scout has only ever found this on its own.
                    </p>
                  ) : (
                    <ul className="pattern-pairs">
                      {travelsWith.map((entry) => (
                        <li key={entry.other}>
                          <button type="button" onClick={() => setFocusedService(entry.other)}>
                            {entry.other}
                          </button>
                          <span className="pattern-pair-count">{entry.count}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section className="pattern-block">
                  <h2 className="pattern-label">How Scout detects it</h2>
                  {mixTotal === 0 ? (
                    <p className="pattern-empty">No evidence types recorded.</p>
                  ) : (
                    <ul className="pattern-mix">
                      {Object.entries(mix)
                        .sort((a, b) => b[1] - a[1])
                        .map(([type, n]) => (
                          <li key={type}>
                            <span className="pattern-mix-type">{type}</span>
                            <span className="pattern-mix-track" aria-hidden="true">
                              <span
                                className="pattern-mix-bar"
                                style={{ width: `${(n / mixTotal) * 100}%` }}
                              />
                            </span>
                            <span className="pattern-mix-share">
                              {Math.round((n / mixTotal) * 100)}%
                            </span>
                          </li>
                        ))}
                    </ul>
                  )}
                </section>
              </div>
            );
          })()}

          <h2 className="pattern-label pattern-accounts-label">Who is asking</h2>
        <ol className="demand-list is-accounts">
          {focusedAccounts.map((account) => (
            <li key={account.companyId} className="demand-row">
              <div className="demand-row-head">
                <Link to={`/companies/${account.companyId}`} className="demand-name">
                  {account.companyName}
                </Link>
                <span className="demand-count">{account.opportunities.length}</span>
              </div>
              <span className="demand-track" aria-hidden="true">
                <span
                  className="demand-bar"
                  ref={(node) => {
                    if (node) barRefs.current.set(`a:${account.companyId}`, node);
                    else barRefs.current.delete(`a:${account.companyId}`);
                  }}
                  style={{ width: `${(account.opportunities.length / accountPeak) * 100}%` }}
                />
              </span>
              <ul className="demand-opportunities">
                {account.opportunities.map((o) => (
                  <li key={o.id}>
                    {o.title}
                    {o.priority === 10 && <span className="demand-lead-tag">top of scale</span>}
                  </li>
                ))}
              </ul>
              {/* The generation workflows this page has always carried stay
                  exactly where they were reachable - one row per account
                  rather than one per opportunity, since the request is about
                  the account either way. */}
              <div className="demand-actions">
                {(Object.keys(ACTION_LABELS) as ActionType[]).map((actionType) => {
                  const actionKey = `${account.companyId}-${actionType}`;
                  return (
                    <button
                      key={actionType}
                      type="button"
                      onClick={() => handleAction(account.companyId, actionType)}
                      disabled={triggeringAction === actionKey}
                    >
                      {triggeringAction === actionKey ? "Starting…" : ACTION_LABELS[actionType]}
                    </button>
                  );
                })}
              </div>
            </li>
          ))}
        </ol>
        </>
      ) : (
        /* --- the map: demand by service line ------------------------------ */
        <>
          <ol className="demand-list">
            {live.map((entry) => (
              <li key={entry.service} className="demand-row">
                <button
                  type="button"
                  className="demand-row-head is-control"
                  onClick={() => setFocusedService(entry.service)}
                >
                  <span className="demand-name">{entry.service}</span>
                  <span className="demand-count">{entry.opportunities}</span>
                </button>
                <span className="demand-track" aria-hidden="true">
                  <span
                    className="demand-bar"
                    ref={(node) => {
                      if (node) barRefs.current.set(`s:${entry.service}`, node);
                      else barRefs.current.delete(`s:${entry.service}`);
                    }}
                    style={{ width: `${(entry.opportunities / peak) * 100}%` }}
                  />
                </span>
                <p className="demand-meta">
                  {entry.companies} {entry.companies === 1 ? "company" : "companies"}
                  {/* Depth is the number a bar chart cannot show: the same
                      eleven opportunities mean something different spread
                      over eleven accounts than concentrated in six. */}
                  {entry.depth >= 1.6 && (
                    <span className="demand-depth">
                      · concentrated, {entry.depth.toFixed(1)} per account
                    </span>
                  )}
                  {entry.topPriority === 10 && <span className="demand-lead-tag">top of scale</span>}
                </p>
              </li>
            ))}
          </ol>

          {quiet.length > 0 && (
            /* The honest inverse, and the reason a practice lead opens this
               page at all: services Scout is barely finding work for. */
            <section className="demand-quiet">
              <h2 className="demand-quiet-heading">Little demand found</h2>
              <p className="demand-quiet-note">
                Service lines Scout has matched to two opportunities or fewer across the whole
                portfolio.
              </p>
              <ul className="demand-quiet-list">
                {quiet.map((entry) => (
                  <li key={entry.service}>
                    <button type="button" onClick={() => setFocusedService(entry.service)}>
                      {entry.service}
                      <span className="demand-quiet-count">{entry.opportunities}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
