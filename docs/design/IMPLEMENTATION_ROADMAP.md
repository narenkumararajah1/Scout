# IMPLEMENTATION_ROADMAP.md

# Scout Frontend Implementation Roadmap

## Status

**Active implementation source of truth.** This document tracks real progress and must be updated at the end of every implementation step. It is derived from, and subordinate to, the design specifications in this directory — if this roadmap and a design document ever disagree, the design document wins and this file must be corrected.

---

# Project Goal

Build a production-quality React frontend for Scout that implements every module described in `docs/design/` exactly as specified, targeting the completed Scout V2 scope (Dashboard, Company Intelligence, Opportunity Analysis, Executive Intelligence, Sales Playbook, Meeting Preparation, AI Outreach, Reports, Analytics). Where backend support does not yet exist, the UI is built completely against strongly typed mock data behind a repository/service abstraction, so the interface never differs in shape or behavior based on whether data is real or mocked. `FUTURE_UI_ROADMAP.md`'s Phase 2–4 items (CRM/calendar/email integration, collaboration, predictive intelligence, marketplace, etc.) are explicitly out of scope and appear, at most, as disabled navigation entries where the navigation spec requires them to exist.

---

# Overall Architecture

## Framework

Next.js (App Router) + TypeScript. Chosen because NAVIGATION.md's information architecture (Dashboard → Companies → Company → tabs → Opportunities/Reports/etc.) maps directly onto nested file-based routing and layouts, and because it is the standard modern foundation for an enterprise SaaS product at the quality bar referenced (Linear, Stripe, Datadog). This is a new application; it replaces `frontend/` (Streamlit) entirely rather than running alongside it.

## Folder Structure

```
web/
  app/                      # Next.js App Router — routes only, thin
    (shell)/                # route group sharing the persistent app shell layout
      dashboard/
      companies/[companyId]/{overview,technology,executives,hiring,news,timeline,opportunities,reports,meeting-prep}/
      opportunities/
      reports/
      executive-intelligence/
      sales-playbooks/
      meeting-preparation/
      ai-outreach/
      analytics/
      notifications/
      settings/
  features/                 # one folder per domain, mirrors docs/design/ 1:1
    company-intelligence/
    opportunity-analysis/
    executive-intelligence/
    sales-playbook/
    meeting-preparation/
    ai-outreach/
    reports/
    analytics/
    dashboard/
    (each contains: components/, hooks/, repository.ts, types.ts)
  components/
    ui/                     # design-system primitives (Button, Card, Table, Badge…)
    layout/                 # Sidebar, TopBar, Breadcrumbs, PageHeader
    charts/                 # chart wrappers
    ai/                     # AISummaryPanel, AIRecommendationPanel, ConfidenceIndicator — shared across features
  lib/
    api/                    # HTTP client, query client, error handling
    repositories/           # repository interfaces + mock/real implementations (see Repository Pattern)
    utils/
  styles/                   # design tokens (CSS custom properties), globals
  hooks/                    # cross-cutting hooks (useMediaQuery, useReducedMotion)
  types/                    # shared domain types
```

Rationale: feature folders mirror the design documentation's own module boundaries exactly, so there is never ambiguity about where a piece of a given spec is implemented.

## Routing

File-based, nested, matching NAVIGATION.md's three-level hierarchy (Primary → Page → Context) exactly. Company sub-pages are tabs within a company layout, not flat top-level routes, matching COMPANY_INTELLIGENCE.md's "Secondary Navigation." Every route is deep-linkable, since breadcrumbs (required on every page per NAVIGATION.md) depend on it.

## State Management

- **Server state**: TanStack Query (React Query) for all data fetched through the repository layer — caching, refetch, optimistic updates for mutations (enable/disable company, distribute report, approve outreach draft).
- **Client-only state**: React Context + `useState`/`useReducer` for UI state (sidebar collapsed, active theme, filters, command palette open). No Redux — nothing in the design specs requires state complex enough to justify it.
- **Forms**: React Hook Form + Zod schema validation.

## Repository Pattern

This is the architectural mechanism that satisfies Project Decision #2 (mock data now, real APIs later, UI unaware of the difference).

- Every domain defines a **repository interface** in `features/<domain>/repository.ts` (e.g. `ExecutiveIntelligenceRepository`) describing the operations a page needs (`getExecutives(companyId)`, `getExecutive(id)`, …), returning strongly typed domain models from `types/`.
- Two implementations may exist per interface: `mock<Domain>Repository` (returns typed fixture data, simulates latency, lives entirely client-side) and `api<Domain>Repository` (calls the real FastAPI backend via `lib/api`).
- A single composition point (`lib/repositories/index.ts`) decides which implementation each feature receives, per-domain, via a config flag — not scattered `if (isMock)` checks inside components or hooks.
- Components and hooks depend only on the repository **interface** (constructor-injected via a React Context provider per repository), never on a concrete implementation — swapping mock for real is changing one line in the composition point, with zero UI changes, exactly as Decision #2 requires.
- Repository interfaces are written from the design documentation's data requirements, not from whatever the current backend happens to return — where the current API response shape differs, the `api*Repository` implementation is responsible for mapping it to the documented domain model.

## Styling Strategy

Tailwind CSS, configured to read design tokens (see below) rather than Tailwind's defaults, with Radix UI primitives underneath every interactive composite (Dialog, Tabs, Dropdown, Tooltip, Popover, Combobox) for correct accessibility behavior out of the box. Component style variants (Button's primary/secondary/tertiary/danger, Badge's status colors) are defined with `class-variance-authority` (cva) so variant logic is typed and centralized rather than duplicated per usage site. No CSS-in-JS runtime.

## Design Token Strategy

DESIGN_SYSTEM.md explicitly defers literal palette/scale values to implementation ("the final palette will be defined during implementation"). CSS custom properties in `styles/tokens.css` are the single source of truth for color, spacing, typography, radius, and elevation; Tailwind's config consumes those same custom properties rather than defining parallel values, so there is exactly one place a token can be changed. Both light and dark themes are defined as two value-sets against the same token names — layout and components never branch on theme, only token values change. See Phase 1 for the actual proposed values.

**Reconciled inconsistency**: RESPONSIVENESS.md specifies custom breakpoints (576 / 768 / 992 / 1200 / 1440) that do not match Tailwind's defaults (640 / 768 / 1024 / 1280 / 1536). Tailwind's `theme.screens` is overridden to use the design doc's exact values. The design doc is authoritative.

## Accessibility Strategy

Semantic HTML first; Radix UI for any widget needing focus-trap, roving tabindex, or complex ARIA (dialogs, menus, tabs, comboboxes) rather than hand-rolling it. Design tokens are pre-validated for WCAG 2.2 AA contrast before use. A shared skip-link pattern lives in the app shell. A single `useReducedMotion` hook gates all animation rather than each component reimplementing the media-query check. Every chart component ships with a paired accessible data-table fallback and text summary, per ACCESSIBILITY.md's explicit requirement — this is a hard acceptance criterion, not a stretch goal. axe-core runs against component tests as an automated baseline; manual keyboard-only and screen-reader passes are part of each phase's completion criteria.

## Performance Strategy

Route-level code splitting (automatic via App Router). Table/list virtualization (`@tanstack/react-virtual`) for large datasets per COMPONENT_LIBRARY.md. Per-section skeleton loading rather than per-page — each Company Intelligence tab, for instance, fetches and loads independently, matching the design docs' explicit "widgets should load independently" requirement. Chart libraries and other heavy visualizations are behind dynamic imports so pages that don't need them don't pay for them.

---

# Implementation Phases

## Phase 1 — Design Tokens, Theme System, Typography, Spacing, Color, Icons

**Objective**: Establish the single visual foundation every later phase builds on, per DESIGN_SYSTEM.md.

**Deliverables**:
- Next.js + TypeScript + Tailwind project scaffolded under `web/`.
- `styles/tokens.css`: color palette (light + dark), spacing scale, typography scale, radius scale, elevation/shadow scale, all as CSS custom properties.
- Tailwind config consuming those tokens, with breakpoints overridden to match RESPONSIVENESS.md.
- Font: Inter (variable font), loaded via `next/font` for zero layout shift.
- Icon system: `lucide-react` (tree-shakeable, consistent single style, matches "minimal, purposeful" requirement from DESIGN_SYSTEM.md).
- `ThemeProvider` (light/dark, respecting `prefers-color-scheme`, with a manual override persisted client-side).
- A token reference/preview page (internal, not part of the product IA) to visually verify every token.

**Dependencies**: None.

**Completion Criteria**: Project builds and runs; theme toggle switches every token correctly with no flash of unstyled content; all documented typography levels (Display Title → Helper Text) render with correct hierarchy; color contrast verified against WCAG AA for both themes; no hardcoded colors/spacing/fonts exist outside `tokens.css`.

---

## Phase 2 — Core UI Component Library

**Objective**: Build every primitive and composite component COMPONENT_LIBRARY.md defines as shared infrastructure, before any page depends on them.

**Deliverables**: Buttons (primary/secondary/tertiary/danger/icon, all states), Cards (standard/KPI/executive/opportunity/company/AI insight), Tables (sortable/filterable/paginated/sticky-header/selectable, per COMPONENT_LIBRARY.md), Forms and Inputs (text, textarea, search, dropdown, date picker, toggle, checkbox, radio), Dialogs, Badges, Status Indicators, Loading states (skeleton card/table/chart, spinner, progress bar), Empty states, Error states, Tooltip/Popover/Accordion/Tabs/Divider/Avatar/Tag/Chip utility components.

**Dependencies**: Phase 1.

**Completion Criteria**: Every component matches its COMPONENT_LIBRARY.md specification; keyboard-operable and screen-reader tested; responsive per RESPONSIVENESS.md; documented (props, usage, variants) in a component catalog; no page-specific one-off component exists yet that duplicates something here.

---

## Phase 3 — Application Shell

**Objective**: Build the persistent navigation and layout structure every page renders inside, per NAVIGATION.md.

**Deliverables**: Sidebar (expanded/collapsed, all primary sections per NAVIGATION.md, including disabled entries for out-of-scope Future Roadmap sections where the spec requires the section to exist), Top Navigation Bar (Global Search, Notifications, Theme Toggle, Quick Actions, Profile Menu), Breadcrumbs, PageHeader, skip-links, the root App Router layout wiring it all together, responsive behavior (sidebar → drawer on tablet/mobile per RESPONSIVENESS.md).

**Dependencies**: Phases 1–2.

**Completion Criteria**: Every page in every later phase renders inside this shell with zero shell-specific code in the page itself; navigation matches NAVIGATION.md's structure exactly; keyboard navigable end-to-end; responsive across all five documented breakpoints.

---

## Phase 4 — Dashboard

**Objective**: Implement DASHBOARD.md's Executive Command Center.

**Deliverables**: Welcome section, Executive Summary Card, KPI section, Priority Opportunities, AI Recommendations, Visual Analytics, Activity Timeline, Company Spotlight, Market Intelligence, Executive Activity, Technology Landscape, Recent Reports, Notifications panel, Quick Actions, Saved Companies. Data sourced from real repositories where backend support exists (Companies, Reports, Analytics); mock repositories elsewhere (AI Recommendations, Market Intelligence, Company Spotlight, Executive Activity — see API Integration Plan).

**Dependencies**: Phases 1–3; Company/Report/Analytics repositories (real); Dashboard-specific mock repositories (recommendations, spotlight, market intelligence).

**Completion Criteria**: Every DASHBOARD.md section present and matching spec; independent per-widget loading states; dashboard answers DASHBOARD.md's "Success Criteria" question list; responsive per its documented desktop/tablet/mobile behavior.

---

## Phase 5 — Company Intelligence

**Objective**: Implement COMPANY_INTELLIGENCE.md's full page hierarchy.

**Deliverables**: Company Header, AI Executive Summary, Opportunity Snapshot, Business Overview, Technology Landscape, Strategic Initiatives, Executive Intelligence summary (link to full module), Hiring Intelligence, Recent News, Historical Timeline, Capability Alignment, Recommended Next Actions, Supporting Intelligence, search-within-company. Backed by real Company/Research Session/Signal/Opportunity/CapabilityMatch repositories; mock repositories for News, Risk Indicators, Competitive Position, and any structured field not currently persisted separately from the research summary prose (see API Integration Plan).

**Dependencies**: Phases 1–3; Company Intelligence repositories (real + mock split, see API Integration Plan).

**Completion Criteria**: Matches COMPANY_INTELLIGENCE.md's page structure and Success Criteria question list; each section loads independently; accessible and responsive per its documented requirements.

---

## Phase 6 — Opportunity Analysis

**Objective**: Implement OPPORTUNITY_ANALYSIS.md.

**Deliverables**: Opportunity Overview, Opportunity Score (with explanation), Opportunity Categories, Business Context, Supporting Evidence, AI Reasoning, Confidence Assessment, Business Impact, Capability Alignment, Recommended Services, Opportunity Timeline, Opportunity Risks, Sales Recommendations, Suggested Talking Points, Discovery Questions, Comparison View.

**Dependencies**: Phases 1–3; Opportunity/CapabilityMatch repositories (real); mock repositories for Business Impact classification, Opportunity Risks, Talking Points/Discovery Questions, and Comparison View until the backend exposes these fields.

**Completion Criteria**: Matches OPPORTUNITY_ANALYSIS.md's structure and Success Criteria; confidence is always shown with its underlying reasoning, never a bare number, per the design philosophy's Explainability principle.

---

## Phase 7 — Reports

**Objective**: Implement REPORTS.md.

**Deliverables**: Report browsing/reading UI following the documented structure (Cover → Executive Summary → Key Insights → Detailed Analysis → Supporting Evidence → Visualizations → Recommendations → Next Steps). Company Intelligence Report type backed by the real Report repository; the other six documented report types (Opportunity, Executive Briefing, Meeting Preparation, Sales Playbook, Executive Intelligence, Technology Assessment) backed by mock repositories until backend report-generation exists for them. Export (PDF/PPT/Word/Markdown/HTML) UI present with mock/stub export behavior, since no export pipeline exists yet.

**Dependencies**: Phases 1–3; Report repository (real for one type, mock for six).

**Completion Criteria**: Matches REPORTS.md's structure for every report type; distribution status display reuses the real Distribution/Recipient data already in the backend.

---

## Phase 8 — Analytics

**Objective**: Implement the Analytics section referenced in NAVIGATION.md and DASHBOARD.md's Visual Analytics.

**Deliverables**: Opportunity Trends and Company Trends backed by the real `/analytics` endpoints; Technology Trends, Industry Insights, Hiring Trends, Company Comparisons, Executive Movement, Historical Trends backed by mock repositories until the backend expands to cover them.

**Dependencies**: Phases 1–3; Analytics repository (partially real, partially mock); chart component library (built as part of this phase, shared with Dashboard/Opportunity Analysis where charts are reused).

**Completion Criteria**: Matches CHARTS_AND_VISUALIZATIONS.md's principles for every chart used; every chart has an accessible data-table fallback; real vs. mock data sections are both fully functional from the UI's perspective.

---

## Phase 9 — Remaining V2 Pages and Integrations

**Objective**: Implement every remaining module the design documentation requires for the completed V2 scope, entirely through mock repositories, since no backend support exists for any of them today.

**Sub-phases**:

- **9A — Executive Intelligence** (EXECUTIVE_INTELLIGENCE.md): leadership overview, executive profiles, organizational structure, executive activity, leadership changes, engagement intelligence, talking points, discovery questions, executive timeline.
- **9B — Sales Playbook** (SALES_PLAYBOOK.md): account strategy summary, business challenges, opportunity prioritization, recommended solutions, executive engagement strategy, discovery strategy, value proposition, competitive positioning, objection handling, engagement timeline, sales readiness score.
- **9C — Meeting Preparation** (MEETING_PREPARATION.md): meeting overview, executive brief, objectives, company snapshot, recent activity, executive profiles, business challenges, discussion topics, discovery questions, recommended services, risks, action plan, checklist.
- **9D — AI Outreach** (AI_OUTREACH.md): recipient overview, communication objective, AI context summary, generated draft, personalization, tone selection, human review/approval workflow (mandatory per the design philosophy — AI never sends automatically), supporting intelligence, export options.
- **9E — Notifications** (NAVIGATION.md, COMPONENT_LIBRARY.md): categorized notification center, unread state, live-region announcements.
- **9F — Global Search & Favorites** (NAVIGATION.md): global search across companies/executives/reports/opportunities, recent activity, favorites/saved companies.
- **9G — Settings** (NAVIGATION.md): profile, preferences, theme, notifications, and a clearly scoped subset given no authentication system exists yet (see Risks in the approved implementation plan) — Account/Integrations/API Keys/Security sections render as documented placeholders, not functional flows, until an authentication decision is made.

**Dependencies**: Phases 1–3 for all sub-phases; each sub-phase's own mock repository and types.

**Completion Criteria**: Every sub-phase matches its design document's page structure and Success Criteria; every page is fully navigable and interactive against mock data; each page/component is written against its repository **interface**, so replacing a mock with a real implementation later requires no UI changes; Settings' auth-dependent sections are explicitly and visibly marked as not-yet-functional rather than silently non-functional.

---

# Component Build Order

1. Design tokens (colors, spacing, typography, radius, elevation) — Phase 1
2. Icon wrapper — Phase 1
3. Button (all variants/states) — Phase 2
4. Badge / Status Indicator — Phase 2
5. Card (standard) — Phase 2
6. Skeleton (card/table/chart) — Phase 2
7. Empty State / Error State — Phase 2
8. Text Input / Textarea / Search Bar — Phase 2
9. Dropdown / Select — Phase 2
10. Checkbox / Radio / Toggle — Phase 2
11. Date Picker — Phase 2
12. Dialog — Phase 2
13. Tooltip / Popover — Phase 2
14. Tabs / Accordion — Phase 2
15. Table (sortable/filterable/paginated) — Phase 2
16. Avatar / Tag / Chip / Divider — Phase 2
17. KPI Card — Phase 2 (used first in Phase 4)
18. AI Summary Panel / AI Recommendation Panel / AI Reasoning Panel / Confidence Indicator — Phase 2 (shared across nearly every later phase)
19. Sidebar / Top Navigation Bar / Breadcrumbs / Page Header — Phase 3
20. Company Card / Opportunity Card / Executive Card — Phases 4–6 (built when first needed, reused thereafter)
21. Chart primitives (Line, Bar, Stacked Bar, Donut, KPI Sparkline) — Phase 8 (pulled forward into Phase 4 if Dashboard needs a chart before Phase 8 begins)
22. Chart primitives, advanced (Network Graph, Org Chart, Timeline, Funnel) — Phase 9A/9B as needed

---

# Page Build Order

1. Dashboard — Phase 4
2. Companies (list/manage) — Phase 5 (reuses existing V2 Company Management; brought up to the new design system)
3. Company Intelligence (all tabs) — Phase 5
4. Opportunity Analysis — Phase 6
5. Reports — Phase 7
6. Analytics — Phase 8
7. Executive Intelligence — Phase 9A
8. Sales Playbook — Phase 9B
9. Meeting Preparation — Phase 9C
10. AI Outreach — Phase 9D
11. Notifications — Phase 9E
12. Global Search / Favorites — Phase 9F
13. Settings — Phase 9G

---

# API Integration Plan

## Real Backend Integrations (existing today)

- Companies: list/add/enable/disable/remove — `GET/POST /companies`, `POST /companies/{id}/enable|disable`, `DELETE /companies/{id}`
- Manual Analysis: `POST /companies/{id}/analyze`
- Reports (Company Intelligence Report type only): `GET /companies/{id}/reports`, `GET /reports/{id}`
- Distribution: `POST /reports/{id}/distribute`, `GET /reports/{id}/deliveries`
- Recipients: full CRUD
- Analytics: `GET /analytics/opportunities`, `GET /analytics/companies/{id}/trends`
- System Status: `GET /system/status`
- Conversational Intelligence: `POST /conversation/ask` (powers Global Search's AI-assisted mode, once Phase 9F is reached)

## Mock Repositories (no backend support today)

- Executive Intelligence (entire module)
- Sales Playbook (entire module)
- Meeting Preparation (entire module)
- AI Outreach (entire module)
- Notifications (entire module)
- Global Search index / Favorites / Recently Viewed
- Dashboard: AI Recommendations, Company Spotlight, Market Intelligence, Executive Activity
- Company Intelligence: Recent News, Risk Indicators, Competitive Position, structured Strategic Initiatives (currently unstructured prose in `research_summary`)
- Opportunity Analysis: Business Impact classification, Opportunity Risks, Talking Points, Discovery Questions, Comparison View
- Reports: the six report types beyond Company Intelligence Report; PDF/PPT/Word/Markdown/HTML export
- Analytics: Technology Trends, Industry Insights, Hiring Trends, Company Comparisons, Executive Movement, Historical Trends
- Settings: Account/Integrations/API Keys/Security (pending an authentication decision)

## Future Integrations (explicitly out of scope for this implementation)

Everything in `FUTURE_UI_ROADMAP.md` Phases 2–4: CRM integration, calendar/email integration, task management, shared workspaces/collaboration, workflow automation, predictive intelligence, mobile-specific enhancements, presentation mode, third-party integrations (Salesforce, Slack, Teams, Zoom, LinkedIn, Power BI), marketplace/extensibility.

---

# Quality Checklist

Every feature must satisfy all of the following before it is marked complete and the next phase begins:

- [ ] Matches its design document section by section — no reinterpretation, simplification, or silent deviation.
- [ ] Built from existing reusable components; no page-specific one-off duplicates something in the component library.
- [ ] Uses the repository pattern for all data access; contains no direct fetch calls or hardcoded mock data inline in a component.
- [ ] Fully keyboard operable; tab order is logical; focus is visible and managed correctly (dialogs trap and restore focus).
- [ ] Passes an automated accessibility check (axe-core) with zero critical/serious violations.
- [ ] Responsive and manually verified at all five documented breakpoints (576/768/992/1200/1440).
- [ ] Uses only design tokens — no hardcoded colors, spacing, or font values.
- [ ] Every loading state uses a skeleton matching the final layout; every empty state explains itself and suggests a next action; every error state explains what happened and how to recover.
- [ ] Every AI-generated value (summary, score, recommendation) displays its confidence and supporting evidence — never a bare number or unexplained claim.
- [ ] Animations respect `prefers-reduced-motion` and stay within ANIMATIONS_AND_MICROINTERACTIONS.md's timing guidelines.
- [ ] No console errors or warnings; TypeScript strict mode passes with no `any` escapes introduced.
- [ ] This roadmap document is updated to reflect the work just completed before moving to the next phase.

---

# Progress Log

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — Design Tokens, Theme, Typography, Spacing, Color, Icons | Blocked | Node.js/npm/npx/yarn/pnpm are not installed in this environment (no Homebrew/nvm either) — the project cannot be scaffolded, dependencies cannot be installed, and nothing can be run or verified. Awaiting a decision on how to proceed before any code is written. |
| Phase 2 — Core UI Component Library | Not started | |
| Phase 3 — Application Shell | Not started | |
| Phase 4 — Dashboard | Not started | |
| Phase 5 — Company Intelligence | Not started | |
| Phase 6 — Opportunity Analysis | Not started | |
| Phase 7 — Reports | Not started | |
| Phase 8 — Analytics | Not started | |
| Phase 9 — Remaining V2 Pages and Integrations | Not started | |
