"""Research Agent - company research, company news, technology trends
(Phase 2, Day 6); social/organizational signals: LinkedIn monitoring,
hiring trends, partnerships, and acquisitions (Phase 2, Day 7); and a
merged, deduplicated "unified research package" (Phase 2, Day 9).
"""

from backend.agents.base import BaseAgent
from backend.config import get_settings
from backend.llm_client import generate_completion
from backend.workflow.state import WorkflowState


class ResearchAgent(BaseAgent):
    name = "Research Agent"

    def run(self, state: WorkflowState) -> WorkflowState:
        company = get_settings().target_company

        business_prompt = (
            f'You are researching the company "{company}" for a B2B sales '
            "prospecting workflow. Provide three clearly labeled sections:\n\n"
            "1. Company Research - what the company does, its industry, and "
            "size if known.\n"
            "2. Company News - recent, notable public news or announcements.\n"
            "3. Technology Trends - current high-level trends in AI, Cloud, "
            "and Data Engineering relevant to enterprise technology consulting.\n\n"
            "If you don't have specific information for a section (for "
            "example, you don't recognize the company), say so explicitly "
            "rather than inventing details."
        )
        business_research = generate_completion(business_prompt)

        social_prompt = (
            f'You are researching the company "{company}" for a B2B sales '
            "prospecting workflow. Provide four clearly labeled sections "
            "covering publicly observable social and organizational signals:\n\n"
            "1. LinkedIn Signals - notable LinkedIn presence or public "
            "professional activity, if known.\n"
            "2. Hiring Trends - what kinds of roles the company appears to be "
            "hiring for, if known, and what that might signal about their "
            "priorities.\n"
            "3. Partnerships - notable public partnerships or alliances, if "
            "known.\n"
            "4. Acquisitions - notable public acquisitions (made by or of the "
            "company), if known.\n\n"
            "If you don't have specific information for a section, say so "
            "explicitly rather than inventing details."
        )
        social_intelligence = generate_completion(social_prompt)

        merge_prompt = (
            f'You previously gathered two research summaries about the company "{company}" '
            "for a B2B sales prospecting workflow. Merge them into a single, well-organized "
            "research package: combine related points, remove duplicate or repeated "
            "information, and present a clean, normalized summary covering both business "
            "and social/organizational signals. If either summary says information wasn't "
            "available, preserve that as-is rather than presenting it as a confident fact.\n\n"
            f"Business Research:\n{business_research}\n\n"
            f"Social Intelligence:\n{social_intelligence}"
        )
        unified_research = generate_completion(merge_prompt)

        state.research_output = {
            "target_company": company,
            "sources": {
                "business_research": business_research,
                "social_intelligence": social_intelligence,
            },
            "unified_research": unified_research,
        }
        return state
