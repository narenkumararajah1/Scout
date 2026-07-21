# Opportunity Analysis Design Specification

## Purpose

The Opportunity Analysis module is responsible for transforming raw company intelligence into actionable business opportunities.

Rather than simply identifying potential opportunities, Scout shall explain:

- Why the opportunity exists.
- What evidence supports it.
- How confident Scout is.
- Which Innominds capabilities align with the opportunity.
- What the sales team should do next.

The objective is not to replace sales judgment but to accelerate decision-making through AI-powered analysis.

Every opportunity presented by Scout should answer one fundamental question:

**"Why should we pursue this opportunity?"**

---

# Design Objectives

The Opportunity Analysis experience shall:

- Explain opportunities rather than simply listing them.
- Build trust through transparent AI reasoning.
- Connect opportunities to measurable business value.
- Prioritize actionable recommendations.
- Reduce research time.
- Help sales teams focus on the highest-impact opportunities.
- Present information in a structured and repeatable manner.

---

# Opportunity Lifecycle

Every opportunity shall move through the following lifecycle.

Intelligence Collection

↓

Pattern Detection

↓

AI Reasoning

↓

Opportunity Identification

↓

Evidence Validation

↓

Capability Alignment

↓

Confidence Assessment

↓

Recommended Actions

↓

Sales Follow-up

Users should understand where an opportunity sits within this lifecycle.

---

# Opportunity Overview

Every opportunity page shall begin with a concise overview.

Display:

- Opportunity Title
- Company Name
- Opportunity Type
- Opportunity Score
- Priority Level
- Confidence Score
- Estimated Business Value
- Estimated Sales Effort
- Last Updated

The overview should provide enough information for users to quickly determine whether further investigation is worthwhile.

---

# Opportunity Score

Scout shall calculate an overall Opportunity Score.

The score should summarize the attractiveness of the opportunity based on multiple contributing factors.

Potential inputs include:

- Technology investments
- Hiring trends
- Executive changes
- Strategic initiatives
- Public announcements
- Company growth
- Industry trends
- Capability alignment
- Historical engagement (Future)
- Internal organizational knowledge (Future)

The score should always be accompanied by an explanation.

Users should never see a score without understanding how it was derived.

---

# Opportunity Categories

Scout shall classify opportunities into meaningful categories.

Examples include:

Cloud Modernization

Artificial Intelligence

Data Engineering

Application Modernization

Platform Engineering

Quality Engineering

Automation

Cybersecurity

Digital Transformation

Infrastructure Modernization

Customer Experience

Analytics

Operational Efficiency

Cost Optimization

Industry-Specific Initiatives

A company may contain multiple active opportunities.

---

# Business Context

Each opportunity shall explain the surrounding business context.

Examples:

The company has increased hiring in cloud engineering.

Recent acquisitions suggest infrastructure integration.

Leadership changes indicate digital transformation.

Growing AI investment aligns with generative AI adoption.

Business context should establish why the opportunity exists.

---

# Supporting Evidence

Every recommendation must include supporting evidence.

Evidence may include:

Recent news

Executive statements

Hiring activity

Technology stack

Job descriptions

Partnerships

Acquisitions

Press releases

Annual reports

Financial announcements

Public technical documentation

Evidence should be presented as structured insights rather than raw links.

---

# AI Reasoning

Scout shall explain its reasoning in natural language.

Example:

"Recent hiring across multiple AI engineering teams, combined with executive discussions around digital transformation, suggests an expanding investment in enterprise AI initiatives."

The explanation should read like an experienced consultant's assessment.

Avoid technical AI terminology.

---

# Confidence Assessment

Every opportunity shall include a confidence score.

Confidence represents how strongly the available evidence supports the recommendation.

Confidence should be categorized as:

Very High

High

Moderate

Low

Experimental

Confidence should never imply certainty.

Instead, it should communicate AI confidence in the available evidence.

---

# Business Impact

Scout shall estimate the potential business impact.

Possible classifications include:

Transformational

High

Medium

Low

Unknown

Business impact should consider:

Customer value

Project complexity

Potential engagement size

Strategic importance

Long-term relationship potential

---

# Capability Alignment

Every opportunity shall map directly to relevant Innominds services.

Each recommendation should explain:

Recommended Capability

Business Challenge

Why It Fits

Expected Customer Value

Potential Engagement Type

Relevant Success Areas

Capability alignment should be one of the strongest sections within the analysis.

---

# Recommended Services

Scout should recommend services such as:

AI Solutions

Cloud Services

Platform Engineering

Application Modernization

Quality Engineering

Automation

Cybersecurity

Data Engineering

Digital Transformation

Recommendations should always include supporting reasoning.

---

# Opportunity Timeline

Whenever possible, Scout shall visualize how the opportunity developed.

Example timeline:

Executive hired

↓

Cloud migration announced

↓

Engineering hiring increased

↓

AI investment expanded

↓

Opportunity identified

Users should understand the progression of events.

---

# Opportunity Risks

Every opportunity should include potential risks.

Examples:

Budget constraints

Leadership uncertainty

Competitive landscape

Technology maturity

Limited evidence

Economic conditions

Internal priorities

Risks should help sales teams prepare realistic expectations.

---

# Sales Recommendations

Scout shall provide practical next steps.

Examples:

Research executive priorities

Generate executive briefing

Prepare discovery questions

Create outreach email

Schedule introductory meeting

Monitor hiring activity

Compare competitors

Recommendations should be ordered by priority.

---

# Suggested Talking Points

Scout should generate initial conversation topics.

Examples:

Cloud modernization

Operational efficiency

AI adoption

Platform scalability

Customer experience

Data modernization

Talking points should support consultative selling.

---

# Discovery Questions

Scout shall recommend thoughtful discovery questions.

Examples:

How is your organization approaching AI adoption?

What modernization initiatives are planned over the next year?

Which technology platforms are currently being evaluated?

Questions should encourage meaningful conversations rather than product pitches.

---

# Visualizations

Opportunity pages should emphasize visual storytelling.

Suggested visualizations include:

Opportunity Score Breakdown

Evidence Distribution

Technology Alignment

Business Timeline

Hiring Trends

Capability Mapping

Confidence Indicator

Industry Comparison

Charts should always support business understanding.

---

# Comparison View

Users should be able to compare opportunities across companies.

Comparison metrics may include:

Opportunity Score

Business Value

Confidence

Technology Alignment

Strategic Fit

Estimated Complexity

Industry

Relationship Potential

Comparison should help prioritize sales efforts.

---

# AI Transparency

Every AI-generated recommendation shall clearly indicate:

Reasoning

Supporting Evidence

Confidence

Generation Timestamp

Analysis Version

Users should understand why the recommendation exists.

---

# Refresh Analysis

Users should be able to request updated analysis.

Scout shall indicate:

Analysis Date

Latest Intelligence

Changes Since Previous Analysis

New Opportunities

Removed Opportunities

Confidence Changes

---

# Accessibility

Opportunity Analysis shall support:

Keyboard navigation

Screen readers

High contrast

Responsive layouts

Accessible charts

Logical reading order

---

# Responsive Design

Desktop

Multi-panel analysis layout.

Tablet

Adaptive card layout.

Mobile

Single-column presentation with expandable sections.

No analytical functionality should be removed on smaller devices.

---

# Future Enhancements

Future versions may include:

Predictive opportunity forecasting

CRM opportunity synchronization

Relationship scoring

Buying intent detection

Proposal generation

Competitive positioning

Revenue forecasting

Multi-company opportunity clustering

Industry benchmarking

Executive influence mapping

---

# Success Criteria

A successful Opportunity Analysis page enables users to answer the following questions within three minutes:

- Why does this opportunity exist?
- What evidence supports it?
- How confident is Scout?
- Which services should we recommend?
- Who should we contact?
- What should we discuss?
- What risks should we consider?
- What should we do next?

If these questions cannot be answered quickly and confidently, the experience should be redesigned.

---

# Final Principle

Opportunity Analysis is the bridge between intelligence and action.

Scout should not merely discover opportunities—it should explain them, validate them, prioritize them, and help the sales team confidently pursue them.

Every opportunity should move the user one step closer to a meaningful customer engagement.

---

**Status:** Active Opportunity Analysis Specification

**Priority:** Highest

**Applies To:** Opportunity Analysis Module