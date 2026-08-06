// Have we done this before?
//
// Purpose. Every other page in Scout runs Scout's agenda - it decides what
// to surface and you read it. This is the only page where you set the
// question, and the only one that reaches across the whole corpus rather
// than one account: 81 ingested case studies of work Innominds has actually
// delivered, plus the capability model, retrieved and cited.
//
// So its question is the one a seller asks before every call - "have we done
// this before?" - and the answer has to be checkable, because an
// uncheckable answer about your own delivery history is worse than no
// answer.
//
// The signature interaction follows from what the backend already returns
// and the page was throwing away. Answers come back with inline [1]/[2]
// markers, and knowledge_sources carries the passage each one refers to,
// its relevance score and a link into the Library. The old page rendered
// the markers as dead plain text and hid the passages in a collapsed
// <details>, leaving the reader to map one to the other by counting. Here
// the marker is the interaction: press [1] and the passage that produced
// that sentence surfaces, scored.
//
// Ask Scout / Scout Copilot (roadmap Phase 2: Core AI Experience).
// Still a conversational Q&A over Scout's already-persisted
// intelligence that never triggers new research - history is kept in
// this page's own state only (resent to the backend each question so
// the LLM has conversational context, but nothing is persisted
// server-side, so it's lost on refresh, matching V2's original
// behavior). New in this phase: optional page context (a ?companyId=
// deep link from a company's page, or the picker below, scopes the
// conversation to that company and unlocks one-click generation
// actions - reusing the existing, already-safe/rate-limited
// GenerationJob endpoints unchanged), Markdown-rendered answers, and
// related-company links when no company is in focus.
import { useState, type ChangeEvent, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { EmptyState } from "../components/ui/EmptyState";
import { ToastContainer } from "../components/ui/Toast";
import { useCompanies } from "../hooks/useCompanies";
import { useCompany } from "../hooks/useCompany";
import { useToasts } from "../hooks/useToasts";
import { conversationService } from "../services/conversationService";
import { meetingBriefService } from "../services/meetingBriefService";
import { outreachDraftService } from "../services/outreachDraftService";
import { v3ReportService } from "../services/v3ReportService";
import type { ConversationTurn, RelatedCompany, SuggestedAction } from "../types/conversation";
import type { KnowledgeReference } from "../types/knowledgeDocument";
import { getErrorMessage } from "../utils/errors";

interface ConversationEntry {
  id: string;
  question: string;
  answer: string | null;
  error: string | null;
  relatedCompanies: RelatedCompany[];
  suggestedActions: SuggestedAction[];
  knowledgeSources: KnowledgeReference[];
}

// How many prior turns get resent to the backend for conversational
// context - bounded so the prompt doesn't grow unbounded over a long
// session.
const HISTORY_TURNS_SENT = 5;

// The model writes citations as bare "[1]" which Markdown renders as literal
// text. Rewriting them to links lets react-markdown hand them to a component
// override, so the marker becomes a control without adding a rehype-raw
// dependency or hand-parsing the AST. Only markers that actually have a
// matching source are converted - a model that cites [7] when four passages
// came back should not produce a control that resolves to nothing.
function linkCitations(answer: string, sourceCount: number): string {
  // The model cites both singly ("[1]") and in groups ("[1, 4]",
  // "[1, 3, 4]"). Matching only the single form left every grouped citation
  // as dead text - which in a real answer was most of them - so each number
  // in a group becomes its own control and they sit adjacent.
  return answer.replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (whole, group: string) => {
    const indexes = group.split(",").map((part) => Number(part.trim()));
    const resolvable = indexes.every((i) => i >= 1 && i <= sourceCount);
    // A model that cites [7] when four passages came back should not produce
    // a control that resolves to nothing - leave the whole group alone.
    if (!resolvable) return whole;
    return indexes.map((i) => `[${i}](#cite-${i})`).join("");
  });
}

export function AskScoutPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const companyId = searchParams.get("companyId") ?? undefined;
  const companiesQuery = useCompanies();
  const focusCompanyQuery = useCompany(companyId);
  const { toasts, pushToast, dismissToast } = useToasts();

  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ConversationEntry[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [triggeringAction, setTriggeringAction] = useState<string | null>(null);
  // Which passage is open, keyed by "<entry id>:<citation number>" so two
  // answers on screen never fight over the same open source.
  const [openCitation, setOpenCitation] = useState<string | null>(null);

  const askMutation = useMutation({
    mutationFn: (askedQuestion: string) => {
      const priorTurns: ConversationTurn[] = history
        .filter((entry): entry is ConversationEntry & { answer: string } => entry.answer !== null)
        .slice(0, HISTORY_TURNS_SENT)
        .map((entry) => ({ question: entry.question, answer: entry.answer }))
        .reverse();
      return conversationService.ask(askedQuestion, companyId, priorTurns);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) {
      setValidationError("Enter a question.");
      return;
    }
    setValidationError(null);

    const entryId = `${Date.now()}`;
    askMutation.mutate(trimmed, {
      onSuccess: (result) => {
        setHistory((current) => [
          {
            id: entryId,
            question: trimmed,
            answer: result.answer,
            error: null,
            relatedCompanies: result.related_companies,
            suggestedActions: result.suggested_actions,
            knowledgeSources: result.knowledge_sources ?? [],
          },
          ...current,
        ]);
      },
      onError: (error) => {
        setHistory((current) => [
          {
            id: entryId,
            question: trimmed,
            answer: null,
            error: getErrorMessage(error),
            relatedCompanies: [],
            suggestedActions: [],
            knowledgeSources: [],
          },
          ...current,
        ]);
      },
    });
    setQuestion("");
  }

  function handleClearFocus() {
    setSearchParams({});
  }

  function handleCompanyPick(event: ChangeEvent<HTMLSelectElement>) {
    if (event.target.value) {
      setSearchParams({ companyId: event.target.value });
    } else {
      setSearchParams({});
    }
  }

  async function handleSuggestedAction(action: SuggestedAction) {
    const actionKey = `${action.company_id}-${action.action_type}`;
    setTriggeringAction(actionKey);
    try {
      if (action.action_type === "meeting_brief") {
        await meetingBriefService.generate(action.company_id);
      } else if (action.action_type === "outreach_draft") {
        await outreachDraftService.generate({
          companyId: action.company_id,
          outreachType: "Email",
          talkingPoints: [],
        });
      } else {
        await v3ReportService.generate(action.company_id);
      }
      pushToast(`${action.label} started - open the company page to watch it finish.`, "success");
    } catch (error) {
      pushToast(getErrorMessage(error), "error");
    } finally {
      setTriggeringAction(null);
    }
  }

  return (
    <div className="ask-scout-page">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      <div className="ask-rail">
        <span className="ask-rail-lead">
          <span className="ask-rail-dot" aria-hidden="true" />
          Answering from what Scout already knows
        </span>
        <span className="ask-rail-sep" aria-hidden="true" />
        <span>never runs new research</span>
      </div>

      <header className="ask-head">
        <h1 className="ask-title">Have we done this before?</h1>
        <p className="ask-subtitle">
          Ask across everything Scout holds &mdash; the companies it watches and the work Innominds
          has already delivered. Every claim it makes carries the passage it came from.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="ask-form">
        <div className="ask-field">
          <input
            type="text"
            placeholder={
              companyId
                ? `Ask about ${focusCompanyQuery.data?.name ?? "this company"}…`
                : "e.g. What IoT work have we delivered before?"
            }
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            aria-label="Your question"
          />
          <button type="submit" className="primary-button" disabled={askMutation.isPending}>
            {askMutation.isPending ? "Thinking…" : "Ask"}
          </button>
        </div>

        <div className="ask-scope">
          {companyId ? (
            <span className="ask-scope-active">
              Scoped to <strong>{focusCompanyQuery.data?.name ?? "this company"}</strong>
              <button type="button" onClick={handleClearFocus}>
                Ask across everything instead
              </button>
            </span>
          ) : (
            (companiesQuery.data ?? []).length > 0 && (
              <label className="ask-scope-picker">
                Asking across all {(companiesQuery.data ?? []).length} companies
                <select value="" onChange={handleCompanyPick}>
                  <option value="">Narrow to one…</option>
                  {(companiesQuery.data ?? []).map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              </label>
            )
          )}
        </div>
        {validationError && <p className="form-error">{validationError}</p>}
      </form>

      {history.length === 0 ? (
        <EmptyState message="Nothing asked yet. Scout answers from what it has already gathered - it will not go and research something new." />
      ) : (
        <ol className="ask-thread">
          {history.map((entry) => (
            <li key={entry.id} className="ask-turn">
              <p className="ask-question">{entry.question}</p>

              {entry.error ? (
                <p className="form-error">Could not get an answer: {entry.error}</p>
              ) : (
                <div className="ask-answer-block">
                  <div className="ask-answer">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        // The citation marker. Rendered as a real button so
                        // it is reachable by keyboard and announces its
                        // state - a superscript span would be invisible to
                        // anyone not using a mouse.
                        a: ({ href, children, ...rest }) => {
                          const match = /^#cite-(\d+)$/.exec(href ?? "");
                          if (!match) {
                            return (
                              <a href={href} {...rest}>
                                {children}
                              </a>
                            );
                          }
                          const index = Number(match[1]);
                          const key = `${entry.id}:${index}`;
                          const isOpen = openCitation === key;
                          return (
                            <button
                              type="button"
                              className={isOpen ? "cite is-open" : "cite"}
                              aria-expanded={isOpen}
                              aria-label={`Source ${index}${
                                entry.knowledgeSources[index - 1]?.name
                                  ? `: ${entry.knowledgeSources[index - 1].name}`
                                  : ""
                              }`}
                              onClick={() => setOpenCitation(isOpen ? null : key)}
                            >
                              {index}
                            </button>
                          );
                        },
                      }}
                    >
                      {linkCitations(entry.answer ?? "", entry.knowledgeSources.length)}
                    </ReactMarkdown>
                  </div>

                  {/* The passage behind whichever marker is open. It appears
                      under the answer rather than in a tooltip because these
                      run to ~900 characters - a hover card would be
                      unreadable and unreachable by keyboard. */}
                  {(() => {
                    const openIndex = openCitation?.startsWith(`${entry.id}:`)
                      ? Number(openCitation.split(":")[1])
                      : null;
                    const source = openIndex ? entry.knowledgeSources[openIndex - 1] : null;
                    if (!source) return null;
                    return (
                      <aside className="cite-panel" aria-live="polite">
                        <header className="cite-panel-head">
                          <span className="cite-panel-index">{openIndex}</span>
                          <span className="cite-panel-name">
                            {source.name ?? source.label ?? "Retrieved passage"}
                          </span>
                          {source.relevance !== null && (
                            <span
                              className="cite-panel-relevance"
                              title="How closely this passage matched the question"
                            >
                              {Math.round(source.relevance * 100)}% match
                            </span>
                          )}
                          {source.document_id && (
                            <Link to={`/knowledge/${source.document_id}`}>Open in Library</Link>
                          )}
                        </header>
                        <p className="cite-panel-content">{source.content}</p>
                      </aside>
                    );
                  })()}

                  {/* Everything Scout drew on, whether or not the model
                      cited it inline. Two kinds come back - ingested case
                      studies and capability definitions - and the
                      distinction matters: one is proof we did the work, the
                      other is a claim that we can. */}
                  {entry.knowledgeSources.length > 0 && (
                    <p className="ask-grounding">
                      Drawn from{" "}
                      {entry.knowledgeSources.filter((s) => s.document_id).length > 0 && (
                        <>
                          {entry.knowledgeSources.filter((s) => s.document_id).length} case-study
                          passage
                          {entry.knowledgeSources.filter((s) => s.document_id).length === 1
                            ? ""
                            : "s"}
                        </>
                      )}
                      {entry.knowledgeSources.filter((s) => s.document_id).length > 0 &&
                        entry.knowledgeSources.filter((s) => !s.document_id).length > 0 &&
                        " and "}
                      {entry.knowledgeSources.filter((s) => !s.document_id).length > 0 && (
                        <>
                          {entry.knowledgeSources.filter((s) => !s.document_id).length} capability
                          definition
                          {entry.knowledgeSources.filter((s) => !s.document_id).length === 1
                            ? ""
                            : "s"}
                        </>
                      )}
                      . Press a number in the answer to read it.
                    </p>
                  )}

                  {entry.relatedCompanies.length > 0 && (
                    <div className="ask-related">
                      <span className="ask-related-label">Accounts this touches</span>
                      {entry.relatedCompanies.map((company) => (
                        <Link key={company.id} to={`/companies/${company.id}`}>
                          {company.name}
                        </Link>
                      ))}
                    </div>
                  )}

                  {entry.suggestedActions.length > 0 && (
                    <div className="ask-actions">
                      {entry.suggestedActions.map((action) => {
                        const actionKey = `${action.company_id}-${action.action_type}`;
                        return (
                          <button
                            key={action.action_type}
                            type="button"
                            onClick={() => handleSuggestedAction(action)}
                            disabled={triggeringAction === actionKey}
                          >
                            {triggeringAction === actionKey ? "Starting…" : action.label}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}

    </div>
  );
}
