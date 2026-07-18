"""Prompts for the V2 Enhanced Research Engine (Phase 4).

Four prompts, matching the four generate_completion calls in
backend/services/research_service.py: two research calls covering
FR-004 through FR-008's categories, a merge (mirroring V1's
ResearchAgent), and a new signal-extraction call.
"""


def build_company_technology_prompt(company_name: str) -> str:
    return (
        f'You are researching the company "{company_name}" for a B2B sales '
        "prospecting workflow at Innominds, a technology consulting firm. "
        "Provide three clearly labeled sections:\n\n"
        "1. Company Information - overview, products/services, industry, "
        "geographic presence, and public financial information if known.\n"
        "2. Technology Initiatives - cloud adoption, AI initiatives, platform "
        "modernization efforts, and specific technologies in use (for "
        "example AWS, Azure, Google Cloud, Databricks, Snowflake, "
        "Kubernetes, GenAI/Agentic AI platforms).\n"
        "3. Business Trends - broader trends relevant to this company's "
        "industry and technology direction.\n\n"
        "If you don't have specific information for a section, say so "
        "explicitly rather than inventing details."
    )


def build_organizational_strategic_prompt(company_name: str) -> str:
    return (
        f'You are researching the company "{company_name}" for a B2B sales '
        "prospecting workflow at Innominds. Provide four clearly labeled "
        "sections:\n\n"
        "1. Hiring Activity - hiring trends, growing departments, "
        "frequently requested technologies, and what this signals about "
        "business priorities.\n"
        "2. Leadership Changes - notable recent or current leadership such "
        "as CTO, CIO, VP Engineering, Head of AI, or Digital Transformation "
        "leaders.\n"
        "3. Strategic Initiatives - acquisitions, partnerships, product "
        "launches, funding, and geographic expansion.\n"
        "4. Public Professional Signals - publicly observable professional "
        "network activity or company updates, where appropriate.\n\n"
        "If you don't have specific information for a section, say so "
        "explicitly rather than inventing details."
    )


def build_merge_prompt(company_name: str, company_technology: str, organizational_strategic: str) -> str:
    return (
        f'You previously gathered two research summaries about the company "{company_name}" '
        "for a B2B sales prospecting workflow. Merge them into a single, well-organized "
        "research summary: combine related points, remove duplicate or repeated "
        "information, and present a clean, normalized summary. If either summary says "
        "information wasn't available, preserve that as-is rather than presenting it as "
        "a confident fact.\n\n"
        f"Company & Technology Research:\n{company_technology}\n\n"
        f"Organizational & Strategic Signals:\n{organizational_strategic}"
    )


def build_signal_extraction_prompt(company_name: str, unified_research: str) -> str:
    return (
        f'Based on the following research summary about "{company_name}", extract '
        "discrete business signals - atomic, notable observations that could indicate "
        "a business opportunity. Each signal's type must be exactly one of: technology, "
        "hiring, leadership, strategic. For each signal, provide a short title, a "
        "one-sentence description, its type, and a confidence score from 0.0 to 1.0 "
        "indicating how strongly the research supports it. If the research doesn't "
        "support any signals in a category, don't include one - do not invent signals "
        "that aren't grounded in the research.\n\n"
        "Respond with ONLY a JSON array, no other text, in this exact format:\n"
        '[{"type": "technology", "title": "...", "description": "...", "confidence": 0.8}]\n\n'
        f"Research Summary:\n{unified_research}"
    )
