// The Innominds knowledge behind a generated artifact (V3 Enhancements
// Phase 3B - 08_SALES_CONTENT_ENRICHMENT.md's Explainability section).
//
// **Wording matters here and is deliberate.** This says "grounded in" and
// "was available to Scout", never "sources cited". Phase 3A retrieves
// permissively - similarity, not a hard filter - and the enrichment prompt
// explicitly tells the model to ignore a passage that is not relevant. So
// Scout knows what it *retrieved*, which is verifiable, but not what the
// model *used*, which is not. Labelling these as citations would assert
// something the system cannot check, and a salesperson might then repeat it
// to a customer as a source.
//
// Collapsed by default, matching Ask Scout's citation disclosure from Phase
// 1B, so the two read as one pattern rather than two.
import { useState } from "react";
import { Badge } from "./Badge";
import { Card } from "./Card";
import type { GroundedInItem } from "../../types/groundedIn";

interface GroundedInProps {
  items: GroundedInItem[] | undefined;
  // Rendered as a Card by default. Pass false to embed the list inside an
  // existing card - the Sales Playbook page does this, because its Why
  // Innominds card already owns this content.
  asCard?: boolean;
  title?: string;
}

// "capability_match:Platform Engineering" is how earlier phases stored
// capability evidence; enrichment stores readable "Kind: Name" labels. Both
// legitimately grounded the artifact, so both are shown - but the raw
// prefixed form is tidied rather than displayed as a database value.
function formatSource(source: string): string {
  if (source.startsWith("capability_match:")) {
    return `Capability match: ${source.slice("capability_match:".length)}`;
  }
  return source;
}

function GroundedInList({ items }: { items: GroundedInItem[] }) {
  return (
    <ul className="grounded-in-list">
      {items.map((item) => (
        <li key={item.id} className="grounded-in-item">
          <div className="grounded-in-item-header">
            <span className="grounded-in-source">{formatSource(item.source)}</span>
            {item.confidence_score !== null && (
              <Badge label={`${Math.round(item.confidence_score * 100)}% match`} />
            )}
            {item.url && (
              <a href={item.url} target="_blank" rel="noreferrer noopener">
                Open
              </a>
            )}
          </div>
          <p className="grounded-in-content">{item.content}</p>
        </li>
      ))}
    </ul>
  );
}

export function GroundedIn({ items, asCard = true, title = "What this is grounded in" }: GroundedInProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Nothing retrieved is a normal state - an install with no ingested
  // knowledge, or an artifact generated before Phase 3A. Rendering an empty
  // card would imply something is missing.
  if (!items || items.length === 0) {
    return null;
  }

  const body = (
    <>
      <button
        type="button"
        className="grounded-in-toggle"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
      >
        {isOpen ? "Hide" : "Show"} the {items.length} piece{items.length === 1 ? "" : "s"} of Innominds knowledge
        Scout drew on
      </button>
      {isOpen && (
        <>
          <p className="grounded-in-hint">
            Retrieved and given to Scout when this was generated. Scout may not have used every passage.
          </p>
          <GroundedInList items={items} />
        </>
      )}
    </>
  );

  return asCard ? <Card title={title}>{body}</Card> : body;
}

// Exported separately for the Sales Playbook page, which renders the list
// inline inside its Why Innominds card with no disclosure of its own.
export { GroundedInList };
