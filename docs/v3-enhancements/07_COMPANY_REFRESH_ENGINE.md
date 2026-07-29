# Company Refresh Engine

## Purpose

The Company Refresh Engine replaces Scout's current "Run Analysis" behavior.

Instead of generating another intelligence report, Scout should re-evaluate the company using the latest available information, detect meaningful business changes, update the company's intelligence profile, and surface only what has changed.

The objective is to transform Scout from a report generator into a continuously evolving intelligence platform.

---

# Vision

Every company within Scout should remain a living intelligence profile.

Rather than repeatedly generating static reports, Scout should continuously monitor organizations, identify significant developments, and update intelligence over time.

Users should never need to manually determine whether a company has changed.

Scout should tell them.

---

# Problem Statement

The current Run Analysis workflow generates another report, even when little or nothing has changed.

This results in:

- Duplicate reports
- Repeated information
- Inefficient AI usage
- Additional review effort
- Reduced user value

Instead, the analysis process should refresh intelligence first and generate reports only when requested.

---

# Objectives

The Company Refresh Engine should:

- Refresh company intelligence.
- Detect meaningful changes.
- Compare historical intelligence.
- Update company profiles.
- Update opportunities.
- Refresh executive information.
- Refresh technology intelligence.
- Refresh hiring trends.
- Refresh business developments.

The company profile should always reflect the latest known state.

---

# Refresh Workflow

The refresh process should follow a standardized workflow.

```
Run Analysis
        ↓
Collect Latest Intelligence
        ↓
Validate Sources
        ↓
Compare Previous Snapshot
        ↓
Detect Changes
        ↓
Update Company Intelligence
        ↓
Refresh Opportunities
        ↓
Present Summary
```

The focus should be on identifying meaningful changes rather than generating new documents.

---

# Intelligence Sources

The refresh process should consume all available intelligence sources.

Examples include:

- External Intelligence
- Company Knowledge Engine
- LinkedIn Intelligence
- Company website
- News sources
- Technology signals
- Hiring activity
- Executive changes

As additional integrations are added, they should automatically become part of the refresh pipeline.

---

# Change Detection

The engine should identify meaningful business changes.

Examples include:

- Executive appointments
- Leadership departures
- AI initiatives
- Cloud migrations
- Product launches
- Acquisitions
- Partnerships
- Funding announcements
- Hiring spikes
- Technology adoption
- Organizational restructuring

Minor or duplicate changes should be filtered to reduce noise.

---

# Intelligence Timeline

Every refresh should contribute to a historical timeline.

Examples:

- Intelligence collected
- Opportunities discovered
- Executive changes
- Technology updates
- Hiring trends
- Strategic announcements

Users should be able to review how a company has evolved over time.

---

# Opportunity Refresh

Opportunity analysis should be recalculated only when meaningful intelligence changes occur.

Examples:

- New opportunity identified
- Existing opportunity strengthened
- Opportunity confidence increased
- Opportunity no longer relevant

Scout should explain why opportunity recommendations changed.

---

# Since Last Refresh

After every analysis, Scout should summarize:

- What changed
- What stayed the same
- New opportunities
- Updated risks
- Recommended next actions

Users should understand the latest developments without reviewing the entire company profile again.

---

# Refresh Summary

The refresh summary should answer:

- What changed?
- Why did it change?
- Why does it matter?
- What should I do next?

This summary becomes the primary output of Run Analysis.

---

# Intelligence History

Scout should maintain historical snapshots of company intelligence.

Users should be able to compare:

- Previous state
- Current state
- Trend over time

Historical intelligence should improve strategic planning and account management.

---

# Notifications

Significant refresh events should generate notifications.

Examples:

- Executive change detected
- Opportunity score increased
- New AI initiative identified
- Technology stack changed
- Hiring trend accelerated

Notifications should prioritize meaningful business events over routine updates.

---

# Integration

The Company Refresh Engine should integrate with:

- Company Intelligence
- Opportunity Analysis
- Executive Intelligence
- Reports
- Meeting Briefs
- Sales Playbooks
- Dashboard
- Scout Copilot

Every module should automatically benefit from refreshed intelligence.

---

# Performance

The refresh process should:

- Avoid duplicate processing
- Cache unchanged intelligence where appropriate
- Refresh only affected sections
- Minimize unnecessary AI calls
- Support asynchronous execution

Performance should improve as Scout scales.

---

# Success Criteria

The Company Refresh Engine succeeds when users no longer think of Run Analysis as "Generate another report."

Instead, they should think:

"Update everything Scout knows about this company."

---

# Relationship to Other Documents

Related documents include:

- External Intelligence
- LinkedIn Intelligence
- Company Knowledge Engine
- Visual Intelligence
- Sales Content Enrichment
- API Research Plan

Together these capabilities transform Scout into a continuously evolving intelligence platform rather than a static reporting tool.