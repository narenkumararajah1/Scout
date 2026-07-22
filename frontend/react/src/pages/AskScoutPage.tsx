// Conversational Q&A over Scout's already-persisted intelligence
// (V2->V3 parity pass) - never triggers new research. History is kept
// in this page's own state only, matching V2's Streamlit behavior
// exactly: nothing is persisted server-side, so it's lost on refresh.
import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { conversationService } from "../services/conversationService";
import { getErrorMessage } from "../utils/errors";

interface ConversationEntry {
  id: string;
  question: string;
  answer: string | null;
  error: string | null;
}

export function AskScoutPage() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ConversationEntry[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);

  const askMutation = useMutation({
    mutationFn: (askedQuestion: string) => conversationService.ask(askedQuestion),
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
      onSuccess: (answer) => {
        setHistory((current) => [{ id: entryId, question: trimmed, answer, error: null }, ...current]);
      },
      onError: (error) => {
        setHistory((current) => [
          { id: entryId, question: trimmed, answer: null, error: getErrorMessage(error) },
          ...current,
        ]);
      },
    });
    setQuestion("");
  }

  return (
    <div className="ask-scout-page">
      <h1>Ask Scout</h1>
      <p className="card-description">
        Ask a question about the companies Scout already knows about - this never runs new research, it only
        answers from what's already been gathered.
      </p>

      <Card title="Ask a question">
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
                  <p className="conversation-answer">{entry.answer}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
