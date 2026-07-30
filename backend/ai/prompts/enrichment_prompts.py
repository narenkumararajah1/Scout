"""Shared prompt fragments for Sales Content Enrichment (V3 Enhancements
Phase 3 - docs/v3-enhancements/08_SALES_CONTENT_ENRICHMENT.md).

Every enriched prompt appends the same two pieces: the retrieved knowledge,
and the instruction for how to use it. They live here rather than being
retyped in each prompt builder because that document requires one shared
enrichment pipeline, and four subtly different phrasings of "use this
knowledge" would be four different behaviours in practice.

Both helpers return "" when there is no knowledge to add, so a prompt
builder can interpolate them unconditionally and an install with an empty
corpus produces exactly the prompt it did before this phase.
"""

from typing import Optional


def knowledge_section(enrichment_block: Optional[str]) -> str:
    """The retrieved knowledge, positioned before the output instructions."""
    if not enrichment_block:
        return ""
    return f"{enrichment_block}\n\n"


def grounding_instruction(enrichment_block: Optional[str]) -> str:
    """How the model must treat the retrieved knowledge.

    Three rules, each earning its place:

    - *Prefer* the supplied knowledge over general reasoning. This is the
      whole point of the phase: 08's problem statement is that content is
      "professional but often lacks sufficient organizational context".
    - *Do not invent* case studies, customers, metrics or capabilities.
      Without this the model happily manufactures plausible Innominds
      engagements, which is worse than being generic - a fabricated
      reference is one a salesperson might repeat to a customer.
    - *Say nothing rather than reach* when the knowledge is not relevant.
      A corpus is retrieved by similarity, so some passages will be
      tangential; forcing them in produces contorted justifications.
    """
    if not enrichment_block:
        return ""
    return (
        "\n\nWhen the Innominds knowledge above is relevant, ground your recommendations in it and "
        "name the specific services, accelerators or customer work it describes. Do not invent "
        "customer names, case studies, metrics or capabilities that are not in that knowledge - if "
        "something is not there, leave it out rather than approximating it. If a supplied passage is "
        "not actually relevant to this opportunity, ignore it rather than forcing it in."
    )
