# Scout Documentation

## Purpose

This directory is the top-level documentation index for the Scout project. It exists to help contributors quickly find the right document rather than searching through version history or source code.

Documentation is organized by version, with each version's material kept together in its own folder.

---

## Directory Overview

### docs/V1/

Archived documentation from Scout's original MVP.

V1 documentation is preserved for historical reference only. It describes the system as it was designed and built during the initial implementation and is no longer updated.

### docs/V2/

The active documentation set for Scout's ongoing development.

V2 is the current source of truth. All new planning, requirements, architecture, and decisions are recorded here, and this is the documentation that should guide any new work on the project.

### docs/design/

The permanent UI/UX and Product Design documentation set, established ahead of Scout V3.

Defines how Scout should look, feel, and behave - design intent and standards, not frontend code. Currently placeholder documents being developed one at a time; see [docs/design/README.md](design/README.md).

### docs/beta-deployment/

How to run Scout, as opposed to what it does. Installation runbook, phased
deployment roadmap, configuration reference, acceptance checklist, operations
(backup, restore, logs), troubleshooting, security posture, and the handover
pack for a beta tester.

Read this before deploying anywhere or giving anyone access; see
[docs/beta-deployment/README.md](beta-deployment/README.md).

---

## Where to Start

New contributors should begin with **[docs/V2/README.md](V2/README.md)**, which explains the full V2 documentation set and the recommended reading order.

---

## Documentation Hierarchy

```
docs/
├── README.md            You are here — top-level index
├── V1/                   Archived (historical reference only)
│   ├── README.md
│   ├── PROJECT_CONTEXT.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   └── IMPLEMENTATION_RULES.md
├── V2/                   Active (current source of truth)
│   ├── README.md
│   ├── VISION.md
│   ├── PROJECT_CONTEXT.md
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── ROADMAP.md
│   ├── IMPLEMENTATION_RULES.md
│   ├── DECISIONS.md
│   └── FEATURE_BACKLOG.md
└── design/               Active (placeholders being developed, ahead of V3)
    ├── README.md
    ├── DESIGN_PHILOSOPHY.md
    ├── DESIGN_SYSTEM.md
    ├── NAVIGATION.md
    ├── DASHBOARD.md
    ├── COMPANY_INTELLIGENCE.md
    ├── OPPORTUNITY_ANALYSIS.md
    ├── REPORTS.md
    ├── EXECUTIVE_INTELLIGENCE.md
    ├── SALES_PLAYBOOK.md
    ├── MEETING_PREPARATION.md
    ├── AI_OUTREACH.md
    ├── COMPONENT_LIBRARY.md
    ├── CHARTS_AND_VISUALIZATIONS.md
    ├── ANIMATIONS_AND_MICROINTERACTIONS.md
    ├── RESPONSIVENESS.md
    ├── ACCESSIBILITY.md
    └── FUTURE_UI_ROADMAP.md
```

---

## Summary

| Folder | Status | Use it for |
|---|---|---|
| `docs/V1/` | Archived | Understanding how the original MVP was designed and built |
| `docs/V2/` | Active | Everything related to current and future development |
| `docs/design/` | Active (in progress) | UI/UX and product design standards for Scout, ahead of V3 |

For details on any specific topic — vision, requirements, architecture, data model, roadmap, engineering standards, decisions, or the feature backlog — see the corresponding document under `docs/V2/`, starting from its [README.md](V2/README.md). For design standards, see [docs/design/README.md](design/README.md).
