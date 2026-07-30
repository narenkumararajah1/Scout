"""What Innominds knowledge grounded a generated artifact (V3 Enhancements
Phase 3B - docs/v3-enhancements/08_SALES_CONTENT_ENRICHMENT.md's
Explainability section: "which knowledge influenced it").

**Named `grounded_in`, not `sources` or `citations`, on purpose.** These are
the passages Phase 3A retrieved and put in the prompt. That is knowable and
verifiable. Which of them the model actually leaned on is not - retrieval is
permissive by design (see content_enrichment_service's scoping note), and
the enrichment prompt explicitly tells the model to ignore a passage that
is not relevant. Calling these "citations" would assert something Scout
cannot check; "grounded in" says exactly what happened.

Backed by the existing Evidence layer, so this covers both Phase 3A's
retrieved knowledge and the capability-match evidence earlier phases
already stored against the same artifacts. Both legitimately answer "what
informed this", and the label distinguishes them.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GroundedInItem(BaseModel):
    """One piece of knowledge that was available to the generator.

    `source` is the readable typed label enrichment stored - "Case Study:
    Meridian Health Systems", "Capability: Platform Engineering",
    "capability_match:Platform Engineering" - which is what makes the list
    scannable without opening anything.
    """

    id: str
    source: str
    content: str
    url: Optional[str] = None
    confidence_score: Optional[float] = None
    retrieved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


def build_grounded_in(evidence_items: list) -> list:
    """Shapes Evidence rows for an artifact detail response.

    Ordered by confidence descending so the strongest match reads first,
    with unscored rows last rather than sorting as zero - an absent score
    means "not measured", not "irrelevant", and capability-match evidence
    from earlier phases is legitimately unscored.
    """
    items = [GroundedInItem.model_validate(item, from_attributes=True) for item in evidence_items]
    return [
        item.model_dump()
        for item in sorted(
            items,
            key=lambda entry: (entry.confidence_score is None, -(entry.confidence_score or 0.0)),
        )
    ]
