# Plan: API Versioning for Content Service

## Goal

The Content Service API needs versioning so we can introduce breaking changes without disrupting existing clients. We'll add a `/v2/` prefix to all endpoints, keep `/v1/` alive for 6 months, then deprecate it.

We're doing this because two teams have complained that API changes broke their integrations unexpectedly. Versioning gives clients a stable surface to pin to.

## Approach

We'll use URL-based versioning (e.g., `/v1/content/:id` and `/v2/content/:id`) rather than header-based versioning because it's easier to see in logs and easier to route at the load balancer level.

## Implementation Steps

### Phase 1: Scaffold v2 routes (Week 1)

- Add a `/v2/` router in `services/content/router.go`
- v2 handlers live in `services/content/handlers/v2/`
- v1 handlers stay in `services/content/handlers/` (no moves)
- Wire v2 into the main router in `cmd/content-service/main.go`

### Phase 2: Implement v2 endpoints (Weeks 2–3)

- Port each v1 endpoint to v2, applying the new response shapes per the API spec (TBD — spec is being written by the platform team)
- Add integration tests for each v2 endpoint alongside the handler

### Phase 3: Client migration (Weeks 4–8)

- Notify all known clients of the new v2 endpoints
- Give clients 6 weeks to migrate
- Monitor `/v1/` traffic; send reminders to teams still hitting v1 at weeks 2 and 4

### Phase 4: v1 deprecation

- Add a `Deprecation` response header to all v1 responses
- After 6 months, return HTTP 410 Gone from all v1 endpoints
- Delete v1 handler code

## What We're Not Doing

- We're not supporting multiple versions in perpetuity — 2 versions max at any time
- We're not doing content negotiation via `Accept` headers

## Open Questions

- How do we handle clients that use `/v1/` without any version prefix? (Some older integrations may hit `/content/:id` directly — TBD)
- Do we need to version the webhook payloads too? Probably yes but not in scope for this plan.

