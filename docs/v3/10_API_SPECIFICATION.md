# Scout V3 API Specification

# Introduction

This document defines the REST API specification for Scout V3.

The API serves as the communication layer between the React frontend and the FastAPI backend. All client interactions with Scout occur through these APIs.

The API follows RESTful principles, JSON request/response bodies, stateless communication, and versioned endpoints.

---

# API Principles

Scout APIs shall follow these principles:

- RESTful design
- Versioned endpoints
- JSON request/response format
- Stateless communication
- Consistent response structure
- Secure authentication
- Proper HTTP status codes
- Comprehensive error handling

---

# Base URL

```
/api/v1
```

---

# Authentication

All endpoints, unless explicitly marked as public, require authentication.

Supported authentication methods:

- JWT Bearer Token
- OAuth 2.0 (future)
- Enterprise SSO (future)

Example Header

```
Authorization: Bearer <access_token>
```

---

# Standard Response Format

## Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {}
}
```

---

## Error Response

```json
{
  "success": false,
  "message": "Resource not found.",
  "errors": []
}
```

---

# Authentication APIs

## Login

```
POST /auth/login
```

Purpose

Authenticate a user.

Request

```json
{
  "email": "",
  "password": ""
}
```

Response

- Access Token
- Refresh Token
- User Information

---

## Logout

```
POST /auth/logout
```

Purpose

Invalidate user session.

---

## Refresh Token

```
POST /auth/refresh
```

Purpose

Issue a new access token.

---

# Company APIs

## List Companies

```
GET /companies
```

Returns

- Company summaries
- Pagination metadata

Supports

- Search
- Filtering
- Sorting
- Pagination

---

## Get Company

```
GET /companies/{companyId}
```

Returns

Complete company profile.

---

## Create Company

```
POST /companies
```

Purpose

Add a company to monitoring.

---

## Update Company

```
PUT /companies/{companyId}
```

Purpose

Update company metadata.

---

## Delete Company

```
DELETE /companies/{companyId}
```

Purpose

Remove company from monitoring.

Soft delete is preferred.

---

# Company Discovery APIs

## Search Companies

```
GET /discovery/search
```

Supported Parameters

- Industry
- Technology
- Geography
- Keywords

Returns

Company search results.

---

## Analyze Company

```
POST /discovery/analyze
```

Purpose

Run the Scout intelligence workflow for a newly discovered company.

---

# Intelligence APIs

## Refresh Company Intelligence

```
POST /companies/{companyId}/refresh
```

Purpose

Run the AI workflow for an existing company.

---

## Company Intelligence

```
GET /companies/{companyId}/intelligence
```

Returns

- Company overview
- Technology landscape
- Business initiatives
- Recent activity

---

# Opportunity APIs

## List Opportunities

```
GET /opportunities
```

Supports

- Search
- Filtering
- Sorting

---

## Get Opportunity

```
GET /opportunities/{opportunityId}
```

Returns

Complete opportunity details.

---

## Opportunity Analysis

```
POST /companies/{companyId}/opportunities/analyze
```

Purpose

Generate AI opportunity analysis.

---

# Executive APIs

## List Executives

```
GET /companies/{companyId}/executives
```

---

## Executive Details

```
GET /executives/{executiveId}
```

---

## Executive Engagement Strategy

```
GET /executives/{executiveId}/engagement
```

Returns

- Conversation starters
- Discovery questions
- Engagement recommendations

---

# Sales Playbook APIs

## Generate Sales Playbook

```
POST /companies/{companyId}/playbook
```

Returns

AI-generated sales strategy.

---

## Get Sales Playbook

```
GET /playbooks/{playbookId}
```

---

# Meeting APIs

## Generate Meeting Brief

```
POST /companies/{companyId}/meeting-brief
```

Returns

Meeting preparation document.

---

## Get Meeting Brief

```
GET /meeting-briefs/{briefId}
```

---

# Outreach APIs

## Generate Outreach

```
POST /companies/{companyId}/outreach
```

Supported Types

- Email
- LinkedIn
- Follow-up
- Meeting Request

---

## List Outreach Drafts

```
GET /outreach
```

---

## Get Outreach Draft

```
GET /outreach/{draftId}
```

---

# Reports APIs

## Generate Report

```
POST /companies/{companyId}/reports
```

---

## List Reports

```
GET /reports
```

---

## Report Details

```
GET /reports/{reportId}
```

---

## Delete Report

```
DELETE /reports/{reportId}
```

---

# Analytics APIs

## Dashboard Analytics

```
GET /analytics/dashboard
```

Returns

- KPIs
- Opportunity metrics
- Company metrics

---

## Technology Trends

```
GET /analytics/technology
```

---

## Opportunity Trends

```
GET /analytics/opportunities
```

---

## Hiring Trends

```
GET /analytics/hiring
```

---

# Notification APIs

## List Notifications

```
GET /notifications
```

---

## Mark Notification Read

```
PATCH /notifications/{notificationId}
```

---

## Delete Notification

```
DELETE /notifications/{notificationId}
```

---

# Search APIs

## Global Search

```
GET /search
```

Supports

- Companies
- Executives
- Reports
- Opportunities
- Technologies

---

# Knowledge APIs

## Knowledge Search

```
GET /knowledge/search
```

Purpose

Semantic search across the Scout knowledge base.

---

## Knowledge Details

```
GET /knowledge/{knowledgeId}
```

---

# Health APIs

## Health Check

```
GET /health
```

Purpose

Service availability check.

---

## Readiness Check

```
GET /ready
```

Purpose

Deployment readiness verification.

---

# Error Codes

Standard HTTP status codes shall be used.

| Code | Meaning |
|-------|----------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# Pagination

Endpoints returning collections shall support pagination.

Query Parameters

```
?page=1
&pageSize=20
```

Response

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "totalItems": 100,
  "totalPages": 5
}
```

---

# Filtering

Collection endpoints may support filtering.

Examples

```
?industry=Healthcare

?technology=Azure

?priority=High

?status=Active
```

---

# Sorting

Example

```
?sort=name

?sort=-createdAt
```

---

# API Versioning

Scout APIs use URI versioning.

Example

```
/api/v1/companies
```

Future versions shall remain backward compatible where possible.

---

# Security

The API shall enforce:

- Authentication
- Authorization
- Input validation
- Rate limiting
- Secure headers
- Audit logging
- Request validation
- HTTPS-only communication

---

# API Design Guidelines

Every endpoint should:

- Have a single responsibility.
- Return consistent response structures.
- Use appropriate HTTP methods.
- Validate all incoming requests.
- Return meaningful error messages.
- Avoid exposing internal implementation details.

---

# Summary

The Scout V3 API provides a secure, versioned, and RESTful interface between the frontend and backend. It exposes endpoints for authentication, company intelligence, opportunity analysis, executive intelligence, reports, analytics, notifications, and AI-powered sales enablement while maintaining consistency, scalability, and enterprise-grade security.