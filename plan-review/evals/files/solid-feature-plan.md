# Plan: Rate Limiting for the Submission API

## Goal

Add per-user rate limiting to `POST /api/submissions` to prevent a single user from flooding the system. Target: 10 submissions per user per minute. Exceeding the limit returns HTTP 429 with a `Retry-After` header.

This is needed because a handful of users running automated scripts are causing p99 latency spikes for everyone else. We confirmed in Datadog that >90% of the spike traffic comes from fewer than 20 user IDs.

## Approach

Use a **sliding window counter in Redis** keyed by `rate_limit:submission:{user_id}`. We chose Redis over an in-process counter because the submission service runs 8 instances and an in-process counter would allow 10 × 8 = 80 requests per minute rather than 10 total.

We chose sliding window over fixed window because fixed window allows bursting up to 20 requests at the boundary between two windows, which defeats the purpose for our use case.

The limit (10/min) and the window (60s) will be configurable via environment variable so we can tune without a deploy.

## Implementation Steps

### Step 1: Add Redis client to the submission service

- The service already has a Redis client in `pkg/redis/client.go` used for session storage. We'll reuse the same client.
- No new infrastructure needed — confirmed the existing Redis instance has headroom (currently at ~12% memory utilization per ops dashboard).

### Step 2: Implement the rate limiter middleware

- New file: `services/submission/middleware/rate_limit.go`
- Implements the sliding window algorithm using `ZADD` + `ZREMRANGEBYSCORE` + `ZCARD` in a single pipeline (atomic via Lua script to avoid TOCTOU race)
- Returns a `RateLimitResult` struct with `{Allowed bool, RetryAfterSeconds int}`
- Unit tests in `services/submission/middleware/rate_limit_test.go` using a Redis test fixture (we already have `pkg/testutil/redis.go` for this)

### Step 3: Wire middleware into the submission handler

- In `services/submission/handlers/submission.go`, wrap the handler with the rate limit middleware
- On 429: return `{"error": "rate_limit_exceeded"}` with `Retry-After: {seconds}` header
- Log rate limit hits at WARN level with `user_id` and `endpoint` fields so we can monitor in Datadog

### Step 4: Add integration test

- In `services/submission/handlers/submission_test.go`, add a test that fires 11 requests in sequence and asserts the 11th gets a 429
- Test also asserts the `Retry-After` header is present and is a positive integer

### Step 5: Deploy and monitor

- Deploy to staging, run load test with `scripts/load_test_submissions.py` (already exists) to verify the limit kicks in
- Deploy to prod behind a feature flag (`ENABLE_SUBMISSION_RATE_LIMIT=true`) — flip the flag after verifying staging
- Monitor error rate and p99 latency in Datadog for 24h post-deploy

## Failure Modes

- **Redis unavailable:** The middleware will fail open (allow the request) rather than fail closed, because it's better to let a few extra submissions through than to take down submissions for all users. This is a deliberate tradeoff — if we need stronger guarantees later, we can revisit.
- **Lua script timeout:** Redis has a 5s default Lua timeout. Our script is 3 operations and will run in microseconds — no concern here.
- **Key expiry:** Keys expire after 2× the window (120s) to prevent unbounded growth. Confirmed this is sufficient for the sliding window invariant.

## Rollback

- If rate limiting causes problems, flip `ENABLE_SUBMISSION_RATE_LIMIT=false` — the middleware short-circuits immediately, no traffic impact.
- No schema or data migrations involved, so rollback has no data consequences.

## What We're Not Doing

- We're not rate limiting other endpoints in this PR — scope is submission only
- We're not building an admin UI to configure limits per-user — static config is sufficient for now

