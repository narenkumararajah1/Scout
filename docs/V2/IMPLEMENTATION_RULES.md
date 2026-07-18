# IMPLEMENTATION_RULES.md

# Scout Version 2 Implementation Rules

## Purpose

This document defines the engineering standards, coding guidelines, and implementation rules for Scout Version 2.

All contributors should follow these rules to ensure consistency, maintainability, and long-term scalability.

These rules apply to all source code, tests, documentation, and architectural decisions.

---

# General Principles

Every implementation should prioritize:

- Simplicity
- Readability
- Maintainability
- Explainability
- Reliability

Avoid unnecessary complexity.

Prefer straightforward solutions over clever solutions.

---

# Development Philosophy

Scout Version 2 is built through incremental improvements.

Do not redesign working Version 1 components unless a clear architectural benefit exists.

Prefer extending existing functionality over replacing it.

Every completed feature should leave the application in a working state.

---

# Code Quality Standards

Code should be:

- Readable
- Modular
- Testable
- Well documented
- Consistent

Future maintainers should understand the purpose of a module without extensive explanation.

---

# Single Responsibility Principle

Every module should have one primary responsibility.

Examples:

Research Service

Responsible only for research.

Capability Matching Service

Responsible only for capability matching.

Reporting Service

Responsible only for report generation.

Avoid services that perform multiple unrelated tasks.

---

# Separation of Concerns

Separate:

- UI
- Business Logic
- AI Logic
- Database Access
- Configuration
- External Services

Business logic should never exist inside UI components.

---

# Service Layer

Business logic should live inside services.

API endpoints should:

- Validate input
- Call services
- Return responses

They should not contain business logic.

---

# Repository Layer

Database operations should be isolated.

Repositories should:

- Read data
- Write data
- Update data
- Delete data

Repositories should not perform business analysis.

---

# AI Agent Responsibilities

Each AI agent owns exactly one responsibility.

Research Agent

Research companies.

Knowledge Agent

Retrieve Innominds knowledge.

Capability Matching Agent

Identify capability alignment.

Opportunity Agent

Generate opportunities.

Content Generation Agent

Generate report content.

Reporting Agent

Assemble reports.

Avoid combining multiple agent responsibilities.

---

# Workflow Coordination

Workflow orchestration should remain independent from business logic.

The Workflow Manager should coordinate execution.

It should not analyze research or generate reports itself.

---

# Data Integrity

Never overwrite historical intelligence.

Research Sessions should remain immutable.

Reports should remain immutable.

Historical records should always be reproducible.

---

# Error Handling

Every failure should:

- Be logged
- Preserve application stability
- Return meaningful messages
- Avoid silent failures

One company failure should not stop processing of others.

---

# Logging

Log meaningful events.

Examples:

Workflow started.

Research completed.

Opportunity generated.

Report created.

Report delivered.

Workflow failed.

Avoid excessive logging that obscures important information.

---

# Configuration

Configuration values should never be hardcoded.

Examples:

API Keys

Model Names

Email Settings

Schedule Times

Database Locations

Configuration should be loaded through centralized configuration management.

---

# Constants

Avoid magic values.

Frequently used values should be defined as constants or configuration.

---

# Environment Variables

Sensitive values should never exist in source code.

Examples:

API Keys

Passwords

Secrets

Tokens

Use environment variables or secure secret management.

---

# Async Operations

Network-bound operations should be asynchronous whenever practical.

Examples:

LLM calls

Web requests

Database operations

Email delivery

Avoid blocking the main execution flow.

---

# AI Prompt Management

Prompts should:

- Be version controlled.
- Be stored separately from business logic.
- Have clear names.
- Be reusable.

Avoid embedding long prompts directly inside source code.

---

# ChromaDB Usage

Knowledge should be retrieved using semantic search.

Do not duplicate knowledge in multiple locations.

Maintain a single authoritative knowledge repository.

---

# Database Rules

SQLite is the source of truth for structured application data.

ChromaDB is the source of truth for semantic knowledge.

Do not duplicate data between storage systems unless necessary.

---

# API Design

APIs should:

- Be RESTful
- Return structured responses
- Validate input
- Handle errors consistently

Future integrations should reuse existing endpoints whenever possible.

---

# Dashboard Rules

The dashboard should remain lightweight.

Complex business logic belongs in backend services.

The dashboard should focus on:

- Display
- User interaction
- Workflow initiation

---

# Testing

Every new feature should include appropriate testing.

Testing should include:

- Unit tests
- Integration tests
- Manual verification

Critical workflows should be validated before merging changes.

---

# Documentation

Significant architectural changes should update documentation.

Documentation should evolve alongside implementation.

Outdated documentation should be corrected promptly.

---

# Dependency Management

Add new dependencies only when they provide clear value.

Avoid introducing libraries for functionality that can be implemented simply with existing tools.

Keep the dependency footprint as small as practical.

---

# Refactoring

Refactor only when it improves:

- Readability
- Maintainability
- Scalability
- Performance

Avoid refactoring solely for stylistic preferences.

---

# Performance

Optimize only after correctness.

Measure performance before introducing optimizations.

Avoid premature optimization.

---

# Explainability

Every business recommendation should be traceable.

Every opportunity should reference supporting evidence.

Every confidence score should be explainable.

Scout should never produce conclusions that cannot be justified.

---

# Security

Follow secure coding practices.

Validate external input.

Protect sensitive information.

Avoid exposing internal implementation details through APIs or reports.

---

# Version Control

Each commit should represent a logical unit of work.

Commit messages should clearly describe the change.

Avoid combining unrelated changes into a single commit.

---

# Pull Request Guidelines

Each pull request should:

- Solve one problem.
- Be fully functional.
- Pass testing.
- Include documentation updates if required.

Large unrelated pull requests should be avoided.

---

# Definition of Done

A task is considered complete only when:

✓ Functionality is implemented.

✓ Tests pass.

✓ Existing functionality continues to work.

✓ Documentation is updated if necessary.

✓ Code follows project standards.

✓ No known regressions exist.

---

# Engineering Philosophy

Scout is intended to become a long-term enterprise platform.

Every implementation decision should favor clarity, maintainability, and reliability over short-term convenience.

Code written today should remain understandable and extensible years into the future.

Quality is a feature.

Maintainability is a requirement.