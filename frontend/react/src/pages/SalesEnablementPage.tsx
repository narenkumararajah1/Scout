// The work queue.
//
// Purpose. The other four pages are all about understanding: the Dashboard
// says what to do, Companies says which account, Company Intelligence says
// why Scout believes something, Analytics says what patterns run across the
// book. None of them is about the work Scout has already produced, or its
// state. That is this page's question, and nothing else asks it:
//
//     What has Scout prepared, and what is waiting on me?
//
// What the production data settled. Across all 19 companies there are 17
// artifacts - 3 playbooks, 3 meeting briefs, 4 outreach drafts, 7 reports -
// and they sit at only 6 companies. Every single one of the four outreach
// drafts is still status "Draft": Scout has written four pieces of outreach
// and not one has been reviewed by a human. That is the whole reason this
// page should exist, and the old page hid it behind a company dropdown that
// showed nothing at all until you picked one.
//
// So: no gate. A work queue you have to configure before it will show you
// anything is not a work queue. The page opens on everything, newest first,
// and leads with the items that are blocked on a person.
//
// The other half of the finding is the gap: 13 of 19 companies have opinions
// from Scout and nothing prepared. That is where "take action" actually
// lives on this page, so it is a section rather than a footnote.
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { ToastContainer } from "../components/ui/Toast";
import { useCompanies } from "../hooks/useCompanies";
import { useExecutiveDashboard } from "../hooks/useExecutiveDashboard";
import { useToasts } from "../hooks/useToasts";
import { meetingBriefService } from "../services/meetingBriefService";
import { outreachDraftService } from "../services/outreachDraftService";
import { salesPlaybookService } from "../services/salesPlaybookService";
import { v3ReportService } from "../services/v3ReportService";
import { getErrorMessage } from "../utils/errors";
import { useQueries } from "@tanstack/react-query";

type ArtifactKind = "playbook" | "brief" | "draft" | "report";

const KIND_LABELS: Record<ArtifactKind, string> = {
  playbook: "Playbook",
  brief: "Meeting brief",
  draft: "Outreach",
  report: "Report",
};

const KIND_ROUTES: Record<ArtifactKind, string> = {
  playbook: "/sales-playbooks",
  brief: "/meeting-briefs",
  draft: "/outreach-drafts",
  report: "/reports",
};

interface Artifact {
  id: string;
  kind: ArtifactKind;
  companyId: string;
  companyName: string;
  title: string;
  createdAt: string | null;
  status: string | null;
}

function relativeDay(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const hours = Math.round((Date.now() - then) / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days}d ago`;
}

export function SalesEnablementPage() {
  const companiesQuery = useCompanies();
  const companies = useMemo(() => companiesQuery.data ?? [], [companiesQuery.data]);
  const dashboardQuery = useExecutiveDashboard(50);
  const { toasts, pushToast, dismissToast } = useToasts();
  const [busy, setBusy] = useState<string | null>(null);
  const [selectedStage, setSelectedStage] = useState<
    "none" | "researched" | "review" | "ready" | "sent" | null
  >(null);

  // One query per company per kind, run in parallel. There is no endpoint
  // that lists artifacts across the whole book - every one of them is scoped
  // to a company - so the queue is assembled client-side rather than the
  // page pretending the gap does not exist by making you pick a company.
  const artifactQueries = useQueries({
    queries: companies.flatMap((company) => [
      {
        queryKey: ["sales-playbooks", company.id],
        queryFn: () => salesPlaybookService.listForCompany(company.id),
      },
      {
        queryKey: ["meeting-briefs", company.id],
        queryFn: () => meetingBriefService.listForCompany(company.id),
      },
      {
        queryKey: ["outreach-drafts", company.id],
        queryFn: () => outreachDraftService.listForCompany(company.id),
      },
      {
        queryKey: ["v3-reports", company.id],
        queryFn: () => v3ReportService.listForCompany(company.id),
      },
    ]),
  });

  // Four list endpoints per company, and every one of them is company-scoped
  // - there is no endpoint that returns artifacts across the book. That is 76
  // requests here, which the browser throttles to six at a time, so waiting
  // for all of them before drawing anything took twenty seconds against
  // production.
  //
  // So the queue renders what has arrived and says it is still gathering.
  // The headline count still waits for the last query, because a number that
  // climbs from 1 to 4 while you read it is worse than no number - but the
  // rows do not, because a row is useful the moment it exists.
  //
  // The real fix is a cross-company artifacts endpoint; this is the honest
  // shape of the page until there is one.
  const settledCount = artifactQueries.filter((q) => !q.isLoading).length;
  const artifactsLoading = settledCount < artifactQueries.length;
  const hasAnyResult = artifactQueries.some((q) => q.data !== undefined);

  const artifacts: Artifact[] = [];
  companies.forEach((company, companyIndex) => {
    const base = companyIndex * 4;
    const kinds: ArtifactKind[] = ["playbook", "brief", "draft", "report"];
    kinds.forEach((kind, offset) => {
      // The four list shapes differ (title vs subject, created_at vs
      // generated_date), so they are read structurally rather than through
      // four near-identical branches.
      const rows = (artifactQueries[base + offset]?.data ?? []) as unknown as Record<
        string,
        unknown
      >[];
      rows.forEach((row) => {
        artifacts.push({
          id: String(row.id),
          kind,
          companyId: company.id,
          companyName: company.name,
          title:
            (row.title as string) ??
            (row.subject as string) ??
            `${KIND_LABELS[kind]} for ${company.name}`,
          createdAt: (row.created_at as string) ?? (row.generated_date as string) ?? null,
          status: (row.status as string) ?? null,
        });
      });
    });
  });


  // --- the pipeline ------------------------------------------------------
  // The page is about work moving toward a customer, not about documents
  // existing. Only outreach carries a lifecycle - Draft, Approved, Sent -
  // because it is the only artifact that ends up in front of anyone. The
  // playbooks, briefs and reports are the evidence that an account has been
  // worked, not stages in their own right.
  //
  // So each account sits at exactly one stage, and the stage is the furthest
  // point any of its work has reached.
  const STAGES = [
    { id: "none", label: "Nothing prepared" },
    { id: "researched", label: "Researched" },
    { id: "review", label: "Awaiting your review" },
    { id: "ready", label: "Ready to send" },
    { id: "sent", label: "Sent" },
  ] as const;
  type StageId = (typeof STAGES)[number]["id"];

  const opportunityCountByCompany = new Map(
    (dashboardQuery.data?.companies ?? []).map((c) => [c.company_id, c.opportunities.length]),
  );

  interface AccountState {
    company: (typeof companies)[number];
    stage: StageId;
    opportunities: number;
    artifacts: Artifact[];
    outreach: Artifact[];
    oldestWaiting: string | null;
  }

  const accounts: AccountState[] = companies
    .filter((c) => !c.archived_at)
    .map((company) => {
      const own = artifacts.filter((a) => a.companyId === company.id);
      const outreach = own.filter((a) => a.kind === "draft");
      const stage: StageId = outreach.some((o) => o.status === "Sent")
        ? "sent"
        : outreach.some((o) => o.status === "Approved")
          ? "ready"
          : outreach.some((o) => o.status === "Draft")
            ? "review"
            : own.length > 0
              ? "researched"
              : "none";
      const waiting = outreach
        .filter((o) => o.status === "Draft")
        .map((o) => o.createdAt)
        .filter(Boolean)
        .sort() as string[];
      return {
        company,
        stage,
        opportunities: opportunityCountByCompany.get(company.id) ?? 0,
        artifacts: own,
        outreach,
        oldestWaiting: waiting[0] ?? null,
      };
    })
    // An account Scout has found nothing at is not stalled, it is just not
    // in the pipeline yet.
    .filter((a) => a.opportunities > 0 || a.artifacts.length > 0);

  const countByStage = STAGES.reduce<Record<StageId, number>>(
    (acc, stage) => ({ ...acc, [stage.id]: accounts.filter((a) => a.stage === stage.id).length }),
    {} as Record<StageId, number>,
  );

  // Open on the earliest stage that actually has something stuck in it and
  // needs a person - that is the answer to "what is blocking revenue".
  const defaultStage: StageId =
    countByStage.review > 0
      ? "review"
      : countByStage.ready > 0
        ? "ready"
        : countByStage.researched > 0
          ? "researched"
          : "none";
  const stage = selectedStage ?? defaultStage;
  const inStage = accounts
    .filter((a) => a.stage === stage)
    .sort((a, b) => (a.oldestWaiting ?? "").localeCompare(b.oldestWaiting ?? "") ||
                    b.opportunities - a.opportunities);


  // Playbook is deliberately absent: the endpoint takes an opportunity_id,
  // not just a company, so a button here would have to pick one of an
  // account's opportunities on the user's behalf without saying which. That
  // choice belongs on the company page where the opportunities are visible.
  type StartableKind = "brief" | "draft" | "report";

  async function startWork(companyId: string, kind: StartableKind, label: string) {
    const key = `${companyId}:${kind}`;
    setBusy(key);
    try {
      if (kind === "brief") await meetingBriefService.generate(companyId);
      else if (kind === "draft")
        await outreachDraftService.generate({ companyId, outreachType: "Email", talkingPoints: [] });
      else await v3ReportService.generate(companyId);
      pushToast(`${label} started - it will appear here when Scout finishes.`, "success");
    } catch (error) {
      pushToast(getErrorMessage(error), "error");
    } finally {
      setBusy(null);
    }
  }

  const isLoading = companiesQuery.isLoading || artifactsLoading;

  return (
    <div className="enablement-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className="queue-rail">
        <span className="queue-rail-lead">
          <span className="queue-rail-dot" aria-hidden="true" />
          {isLoading
            ? "Scout is gathering what it has prepared"
            : `${accounts.length} accounts in the pipeline`}
        </span>
        {!isLoading && (
          <>
            <span className="queue-rail-sep" aria-hidden="true" />
            <span>
              {countByStage.sent === 0
                ? "nothing has reached a customer yet"
                : `${countByStage.sent} reached a customer`}
            </span>
          </>
        )}
      </div>

      <header className="queue-head">
        {/* The count assembles from one query per company per artifact kind,
            so it climbs as they land. Asserting a number mid-flight means
            printing "1 piece of work waiting on you" and then silently
            changing it to four - the headline stays a statement of intent
            until every query has answered. */}
        <h1 className="queue-title">
          {isLoading
            ? "Where the work has stopped"
            : countByStage.review > 0
              ? `${countByStage.review} ${countByStage.review === 1 ? "account is" : "accounts are"} waiting on your review`
              : countByStage.ready > 0
                ? `${countByStage.ready} ready to send`
                : countByStage.none > 0
                  ? `${countByStage.none} ${countByStage.none === 1 ? "account has" : "accounts have"} nothing prepared`
                  : "Nothing is blocked"}
        </h1>
        <p className="queue-subtitle">
          Work moving toward a customer, and where it has stopped. Scout drafts outreach but never
          sends it &mdash; every account below is held up on a person, not on Scout.
        </p>
      </header>

      {artifactsLoading && artifactQueries.length > 0 && (
        <p className="queue-gathering" role="status">
          Gathering &mdash; {settledCount} of {artifactQueries.length} checked
        </p>
      )}

      {companiesQuery.isError ? (
        <ErrorState message={getErrorMessage(companiesQuery.error)} />
      ) : companiesQuery.isLoading || !hasAnyResult ? (
        <LoadingState />
      ) : (
        <>
          {/* --- the pipeline --------------------------------------------
              The page's spine. Every account sits at exactly one stage, and
              the stages read left to right toward a customer. Selecting one
              is how you work it - the signature interaction here is not
              inspecting a thing, it is picking up the stage that is stuck. */}
          <ol className="pipeline" aria-label="Pipeline stages">
            {STAGES.map((s) => (
              <li key={s.id} className={s.id === stage ? "pipeline-stage is-active" : "pipeline-stage"}>
                <button
                  type="button"
                  onClick={() => setSelectedStage(s.id)}
                  aria-pressed={s.id === stage}
                  disabled={countByStage[s.id] === 0}
                >
                  <span className="pipeline-count">{countByStage[s.id]}</span>
                  <span className="pipeline-label">{s.label}</span>
                </button>
              </li>
            ))}
          </ol>

          <section className="stage-panel" aria-live="polite">
            <h2 className="queue-section-label">
              {STAGES.find((s) => s.id === stage)?.label}
              <span className="stage-panel-count">
                {inStage.length} {inStage.length === 1 ? "account" : "accounts"}
              </span>
            </h2>

            {inStage.length === 0 ? (
              <EmptyState message="Nothing is sitting at this stage." />
            ) : (
              <ul className="stage-list">
                {inStage.map((account) => (
                  <li key={account.company.id} className="stage-row">
                    <div className="stage-row-main">
                      <Link to={`/companies/${account.company.id}`} className="stage-company">
                        {account.company.name}
                      </Link>
                      <p className="stage-status">
                        {stage === "review" && account.oldestWaiting && (
                          <>
                            {account.outreach.filter((o) => o.status === "Draft").length} draft
                            {account.outreach.filter((o) => o.status === "Draft").length === 1
                              ? ""
                              : "s"}{" "}
                            written, unread {relativeDay(account.oldestWaiting)}
                          </>
                        )}
                        {stage === "ready" && "Approved and waiting to be sent"}
                        {stage === "sent" && "Outreach has gone out"}
                        {stage === "researched" && (
                          <>
                            {account.artifacts.length} piece
                            {account.artifacts.length === 1 ? "" : "s"} of research prepared, no
                            approach written yet
                          </>
                        )}
                        {stage === "none" && (
                          <>
                            {account.opportunities} open opportunit
                            {account.opportunities === 1 ? "y" : "ies"} and nothing written from
                            them yet
                          </>
                        )}
                      </p>
                      {/* The artifacts are evidence that this account has
                          been worked, not the subject of the row. */}
                      {account.artifacts.length > 0 && (
                        <ul className="stage-evidence">
                          {account.artifacts.slice(0, 4).map((artifact) => (
                            <li key={`${artifact.kind}-${artifact.id}`}>
                              <Link to={`${KIND_ROUTES[artifact.kind]}/${artifact.id}`}>
                                {KIND_LABELS[artifact.kind]}
                              </Link>
                            </li>
                          ))}
                          {account.artifacts.length > 4 && (
                            <li className="stage-evidence-more">
                              +{account.artifacts.length - 4}
                            </li>
                          )}
                        </ul>
                      )}
                    </div>

                    {/* Exactly one move forward per stage. A queue whose rows
                        offer four equal choices is a menu, not a workflow. */}
                    <div className="stage-row-action">
                      {stage === "review" && (
                        <Link
                          to={`${KIND_ROUTES.draft}/${
                            account.outreach.find((o) => o.status === "Draft")?.id ?? ""
                          }`}
                          className="stage-advance"
                        >
                          Read and approve <span aria-hidden="true">&rarr;</span>
                        </Link>
                      )}
                      {stage === "ready" && (
                        <Link
                          to={`${KIND_ROUTES.draft}/${
                            account.outreach.find((o) => o.status === "Approved")?.id ?? ""
                          }`}
                          className="stage-advance"
                        >
                          Open to send <span aria-hidden="true">&rarr;</span>
                        </Link>
                      )}
                      {/* The two early stages are not the same problem, so
                          they do not get the same button. An account with
                          research already done needs an approach written;
                          an account with nothing needs Scout to assemble
                          what it knows first. Offering "draft the outreach"
                          on an account with no prepared material would be
                          asking Scout to write from nothing. */}
                      {stage === "researched" && (
                        <button
                          type="button"
                          className="stage-advance is-button"
                          onClick={() => startWork(account.company.id, "draft", "Outreach")}
                          disabled={busy === `${account.company.id}:draft`}
                        >
                          {busy === `${account.company.id}:draft`
                            ? "Writing…"
                            : "Draft the outreach"}
                        </button>
                      )}
                      {stage === "none" && (
                        <button
                          type="button"
                          className="stage-advance is-button"
                          onClick={() => startWork(account.company.id, "report", "Report")}
                          disabled={busy === `${account.company.id}:report`}
                        >
                          {busy === `${account.company.id}:report`
                            ? "Assembling…"
                            : "Prepare the account"}
                        </button>
                      )}
                      {stage === "sent" && (
                        <Link to={`/companies/${account.company.id}`} className="stage-advance">
                          Open account <span aria-hidden="true">&rarr;</span>
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

        </>
      )}
    </div>
  );
}
