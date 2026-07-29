# IMPLEMENTATION_ROADMAP.md

# Scout Frontend Implementation Roadmap

## Status

**Corrected record, reflecting what was actually built.** The version of this document that existed before this rewrite described a plan (Next.js, Tailwind CSS, Radix UI, a mock/real repository-swap pattern, a Progress Log claiming Phase 1 was "Blocked - Node.js not installed") that was never executed. The real frontend build took a different, simpler path under `docs/v3/16_IMPLEMENTATION_ROADMAP.md`'s Phase 7, using a different stack, and it is now feature-complete. This document is rewritten to describe that reality, not the original plan.

If this roadmap and a design document in this directory ever disagree, the design document wins and this file must be corrected — that governing rule is unchanged.

---

# Project Goal

Scout V3's frontend is a production React application implementing every module described in `docs/design/`: Dashboard, Company Intelligence, Opportunity Analysis, Executive Intelligence, Sales Playbook, Meeting Preparation, AI Outreach, Reports, Analytics, Notifications, Settings, Administration, Ask Scout, and Sales Enablement.

Unlike the original plan (build the UI against mock data behind a repository abstraction, then swap in real APIs later), the backend was built out in step with the frontend, so almost every page reads and writes real data through a live FastAPI + PostgreSQL backend from the start. There is no mock-data layer to retire.

A full V2 → V3 parity review (comparing V2's Streamlit app and V3's React app feature-for-feature) was completed and closed; see `TECH_DEBT.md`'s "Current state (V2->V3 parity pass - feature-complete)" section for the detailed findings and fixes. Scout V3 is a genuine superset of V2.

---

# Overall Architecture

## Framework

**Vite + React 18 + TypeScript** (`frontend/react/`), not Next.js. Routing is client-side via `react-router-dom` (v6), not file-based App Router. This is a from-scratch application; it replaces the retired `frontend/streamlit` (V2) entirely.

## Folder Structure (actual)

```
frontend/react/src/
  api/            # HTTP client (api/client.ts) - auth header injection, 204 handling, error envelope parsing
  services/       # one file per domain - thin functions calling the API client (companyService.ts, reportService.ts, ...)
  hooks/          # TanStack Query hooks wrapping each service (useCompanies, useCompanyReports, useGenerateOutreachDraft, ...)
  types/          # shared domain types, matching backend Pydantic schemas
  contexts/       # AuthContext.ts + AuthProvider.tsx (JWT session state)
  layouts/        # AppLayout, Header, Sidebar (persistent nav shell)
  routes/         # ProtectedRoute
  components/ui/  # Card, Badge, Toast, ConfirmDialog, LoadingState, ErrorState, EmptyState, UserMenu,
                   # OpportunityCard, CapabilityCard, ProseSection, NumberedList, BulletList, ...
  pages/          # one file per route - DashboardPage, CompaniesPage, CompanyDetailsPage, AnalyticsPage,
                   # ReportDetailPage, V3ReportDetailPage, SalesPlaybookDetailPage, MeetingBriefDetailPage,
                   # OutreachDraftDetailPage, SalesEnablementPage, NotificationsPage, AdministrationPage,
                   # AskScoutPage, SettingsPage, LoginPage
  utils/          # presentation-only helpers (reportFormatting.ts, errors.ts, outreachDraft.ts, ...)
  config/         # authConfig.ts (AUTH_REQUIRED flag)
```

Feature folders mirror the design documentation's module boundaries (Company Intelligence, Opportunity Analysis, Sales Playbook, etc.) at the **page and service level**, not as separate `features/<domain>/` directories as originally planned - a flatter `services/` + `hooks/` + `pages/` split proved sufficient at this project's size.

## Routing

Client-side routes registered in `App.tsx`, nested under a persistent `AppLayout` (`Sidebar` + `Header` + scrollable `.app-content`, per the recent persistent-navigation fix). Company sub-pages are tabs within `CompanyDetailsPage`, matching `COMPANY_INTELLIGENCE.md`'s navigation intent, rather than file-based nested routes.

## State Management

- **Server state**: TanStack Query (`@tanstack/react-query` v5) for every API-backed read and write - caching, refetch, mutations (enable/disable company, distribute report, approve/archive/send outreach draft, generate any of the four flagship artifacts). This part of the original plan was followed as written.
- **Client-only state**: React Context (`AuthContext`) plus component-local `useState` for UI state (dropdown/drawer open, form fields, toasts). No Redux, no dedicated client-state library.
- **Forms**: plain controlled inputs with component-local validation. No React Hook Form, no Zod - forms in this app are simple enough that a validation library was not needed.

## Data Access Pattern

There is **no repository interface / mock-vs-real swap layer**. Each domain has a `services/<domain>Service.ts` file that calls `api/client.ts` directly and returns typed data matching the backend's Pydantic schemas, and a `hooks/use<Domain>.ts` file wrapping it in TanStack Query. Pages depend on the hooks directly. This was simpler than the originally planned repository abstraction because the backend was available to build against from early on - there was never a period where the UI needed to run against fixture data instead of a real API.

## Styling Strategy

**Plain, hand-authored CSS** in a single `frontend/react/src/index.css`, using conventional class names (`.card`, `.badge`, `.sidebar`, `.app-header`, `.opportunity-card`, etc.) and standard `@media` breakpoints (768px, 576px) for responsiveness. There is no Tailwind CSS, no CSS-custom-property design-token file, no Radix UI, and no `class-variance-authority` - none of these were adopted. `DESIGN_SYSTEM.md`'s palette/spacing/typography intent is expressed directly as CSS rules rather than through a token pipeline.

## Accessibility

Semantic HTML elements (`<nav>`, `<header>`, `<main>`, `<button>`, proper `<label>`/`<input>` pairing) and ARIA attributes (`aria-expanded`, `aria-haspopup`, `role="menu"`) are used directly in components (e.g. `UserMenu.tsx`, the mobile sidebar drawer) rather than via a component library that provides them automatically. There is no automated accessibility test suite (no axe-core integration) - accessibility has been verified manually per feature during browser verification passes, not enforced by CI.

## Performance

No route-level code splitting, virtualization library, or dynamic chart imports have been introduced - the application has not yet reached a scale where these are necessary. This should be revisited if page weight or list sizes become a real problem; see `PRODUCT_EVOLUTION_BACKLOG.md`'s Infrastructure Improvements section for future candidates.

---

# What Was Actually Built

The detailed, phase-by-phase build history lives in two places rather than being duplicated a third time here:

- **`docs/v3/16_IMPLEMENTATION_ROADMAP.md`** - the roadmap that was actually followed, covering the full backend + frontend build across seven phases (Foundation, Core Backend, Knowledge Platform, AI Intelligence Engine, Business Intelligence, Sales Enablement, Frontend Experience).
- **`TECH_DEBT.md`** - the living log of gaps, fixes, and verification notes recorded as work happened, including the post-Phase-7C V2→V3 parity pass, the report readability redesign, the Meeting Brief generation diagnosis, the outreach workflow redesign, and the persistent-navigation/account-menu work.

Current state, in summary:

- **Every page listed in [Folder Structure](#folder-structure-actual) above exists and is wired to real backend endpoints.** Company Intelligence, Executive Intelligence, Sales Playbook, Meeting Preparation, AI Outreach, Reports, V3 Reports, Analytics, Notifications, Administration (Recipients + Scheduling), and Ask Scout are all real, Postgres-backed, and LLM-backed where AI generation is involved - none of them are mock data, unlike the original plan's assumption that most of these would ship against fixtures.
- **Authentication is fully built, not pending a decision.** JWT issuance, the `User` repository, and every protected endpoint exist; `require_authentication` (backend) and `AUTH_REQUIRED` (frontend, `config/authConfig.ts`) are both currently set to `false` so the app is usable without logging in during this development period. Flipping both back to `true` is the entire rollback - no other code changes are needed.
- **Navigation is a persistent shell**, not a per-page layout: the sidebar and header stay fixed while only page content scrolls, with a hamburger-triggered off-canvas drawer below 768px (mobile/tablet) and a top-right user menu (avatar/initials, Settings, Logout) instead of inline account controls.
- **The environment runs on Vite's dev server (`:5173`) and FastAPI (`:8000`)** against a real PostgreSQL instance (ephemeral `pgserver` in development). Node.js/npm are installed and have been used continuously - the previous Progress Log's "Blocked - Node.js not installed" entry no longer reflects reality and has been removed.

---

# API Integration Plan (actual)

Because the backend was built alongside the frontend, there is no meaningful "real vs. mock" split left to track. Every capability listed in [Core Capabilities](PRODUCT_REQUIREMENTS.md#core-capabilities) is backed by a real endpoint under `/api/v1/`, persisted in PostgreSQL, with AI-generated content (Sales Playbooks, Meeting Briefs, Outreach Drafts, V3 Reports, opportunity analysis, executive intelligence) produced by real LLM calls through `backend/ai/llm_gateway.py`, not fixture data.

The one deliberately-disabled capability is **outbound message delivery** (email/Teams) for Outreach Drafts, which is feature-complete but gated behind an explicit "Send Through Scout" confirmation step, and only actually sends if SMTP/Teams webhook configuration is present in the environment - see `TECH_DEBT.md`'s outreach workflow redesign section.

---

# Quality Checklist

Every feature should satisfy the following before it is considered complete:

- [ ] Matches its design document in `docs/design/` - no silent deviation; if a deviation was necessary, the design document is updated to match, per this directory's own rule.
- [ ] Built from existing reusable components in `components/ui/`; no page-specific one-off duplicates something already there.
- [ ] Data access goes through a `services/` + `hooks/` pair using TanStack Query; no direct `fetch` calls inline in a component.
- [ ] Keyboard operable; focus is visible; interactive elements have appropriate ARIA attributes.
- [ ] Responsive and manually verified at desktop, tablet, and mobile widths (the two breakpoints actually in use: 768px and 576px).
- [ ] Every loading state has a visible loading indicator; every empty state explains itself; every error state surfaces a real message via `utils/errors.ts` / `ErrorState`.
- [ ] Confidence scores and AI-generated recommendations are shown with supporting context, not a bare number.
- [ ] `tsc -b` and `npm run lint` both pass with zero errors/warnings before considering a change done.
- [ ] Verified against a real running backend + Postgres instance in the browser, not just by static type-checking.
- [ ] `TECH_DEBT.md` is updated with any new gap, fix, or verification note discovered while implementing.

---

# Progress Log

| Phase | Status | Notes |
|---|---|---|
| Backend foundation, auth, Postgres migration, AI services (Phases 1-6 of `docs/v3/16_IMPLEMENTATION_ROADMAP.md`) | Complete | See that document and `TECH_DEBT.md` for detail. |
| Frontend Experience (Phase 7A - foundation, Phase 7B - Reports/Analytics/Notifications, Phase 7C - Sales Playbook/Meeting Prep/Outreach/V3 Reports/Settings) | Complete | Scout V3 declared feature-complete at the end of Phase 7C. |
| V2 → V3 parity pass (auth bypass, Remove Company, Recipient Management, Report Distribution, generation UI, Ask Scout, Workflow History, Schedule wiring, Administration page, navigation overhaul, `ConfirmDialog`) | Complete | Verified against a real running backend/frontend, not just by inspection. |
| Report readability redesign (presentation-only formatting) | Complete | No change to underlying report content or generation logic. |
| Meeting Brief generation diagnosis | Resolved | Root cause was a data-sync gap (un-migrated Postgres instance), not a code bug. |
| Outreach workflow redesign (decoupled generation from delivery) | Complete | Verified end-to-end; full backend test suite passing against real Postgres. |
| Persistent navigation, account menu, mobile/tablet drawer | Complete | Sidebar/header fixed while content scrolls; account controls moved to a top-right user menu; mobile/tablet sidebar is now a hamburger-triggered drawer. |

This table will keep growing as new work lands. Entries should stay one line each; anything requiring more explanation belongs in `TECH_DEBT.md`, linked from here rather than duplicated.
