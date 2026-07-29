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
import { Card } from "../components/ui/Card";
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
      <h1>Ask Scout</h1>
      <p className="card-description">
        Ask a question about the companies Scout already knows about - this never runs new research, it only
        answers from what's already been gathered.
      </p>

      <Card title="Ask a question">
        {companyId ? (
          <p className="ask-scout-focus-banner">
            Asking about <strong>{focusCompanyQuery.data?.name ?? "this company"}</strong>.{" "}
            <button type="button" className="ask-scout-clear-focus" onClick={handleClearFocus}>
              Clear
            </button>
          </p>
        ) : (
          (companiesQuery.data ?? []).length > 0 && (
            <select value="" onChange={handleCompanyPick} className="ask-scout-company-picker">
              <option value="">Ask about a specific company (optional)...</option>
              {(companiesQuery.data ?? []).map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          )
        )}
        <form onSubmit={handleSubmit} className="ask-scout-form">
          <input
            type="text"
            placeholder="e.g. Which companies are investing in AI?"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
          {validationError && <p className="form-error">{validationError}</p>}
          <button type="submit" disabled={askMutation.isPending}>
            {askMutation.isPending ? "Thinking..." : "Ask"}
          </button>
        </form>
      </Card>

      <Card title="Conversation">
        {history.length === 0 ? (
          <EmptyState message="No questions asked yet." />
        ) : (
          <ul className="conversation-history">
            {history.map((entry) => (
              <li key={entry.id} className="conversation-entry">
                <p className="conversation-question">{entry.question}</p>
                {entry.error ? (
                  <p className="form-error">Could not get an answer: {entry.error}</p>
                ) : (
                  <>
                    <div className="conversation-answer">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{entry.answer}</ReactMarkdown>
                    </div>
                    {entry.relatedCompanies.length > 0 && (
                      <div className="conversation-related-companies">
                        {entry.relatedCompanies.map((company) => (
                          <Link
                            key={company.id}
                            to={`/companies/${company.id}`}
                            className="conversation-company-chip"
                          >
                            {company.name}
                          </Link>
                        ))}
                      </div>
                    )}
                    {entry.knowledgeSources.length > 0 && (
                      <details className="conversation-sources">
                        <summary>
                          Grounded in {entry.knowledgeSources.length} knowledge{" "}
                          {entry.knowledgeSources.length === 1 ? "passage" : "passages"}
                        </summary>
                        <ol className="conversation-source-list">
                          {entry.knowledgeSources.map((source, index) => (
                            <li key={`${source.source ?? "source"}-${index}`}>
                              <div className="conversation-source-header">
                                <span className="conversation-source-label">{source.label ?? "Knowledge"}</span>
                                {source.document_id && (
                                  <Link to={`/knowledge/${source.document_id}`}>Open in Library</Link>
                                )}
                              </div>
                              <p className="conversation-source-content">{source.content}</p>
                            </li>
                          ))}
                        </ol>
                      </details>
                    )}
                    {entry.suggestedActions.length > 0 && (
                      <div className="conversation-suggested-actions">
                        {entry.suggestedActions.map((action) => {
                          const actionKey = `${action.company_id}-${action.action_type}`;
                          return (
                            <button
                              key={action.action_type}
                              type="button"
                              onClick={() => handleSuggestedAction(action)}
                              disabled={triggeringAction === actionKey}
                            >
                              {triggeringAction === actionKey ? "Starting..." : action.label}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
