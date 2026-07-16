# Agent Authentication Redaction Fix Design

Date: 2026-07-16

## Problem

Node A receives the sanitized result of `wqb auth status`. A valid BRAIN response
contains HTTP 200 and a nonblank `user.id`, but the sensitive token value is
redacted before the node reads it. The current authentication predicate requires
`token.expiry`, so it incorrectly pauses a valid session as `NEEDS_AUTH`.

An unauthenticated HTTP 204 response with no body must also pause rather than
raise `DiscoveryError` and terminate the run as `FAILED`.

## Behavior

- HTTP 401, 403, or 204 returns `NEEDS_AUTH`.
- An explicit boolean `authenticated` or `is_authenticated` remains authoritative.
- Otherwise, a successful response is authenticated when `user.id` is a
  nonblank string.
- Token content, shape, and expiry are not inspected.
- Missing or malformed identity data fails closed as `NEEDS_AUTH`.
- Other malformed successful response shapes continue to fail closed without
  weakening command or artifact redaction.

## Scope

Modify only Node A authentication classification and its focused tests. Do not
change token redaction, cookies, login storage, model routing, workflow routes,
or terminal-state behavior.

## Tests

Add regression coverage proving:

1. HTTP 200 with `user.id` and a redacted token advances to B.
2. HTTP 204 with an empty body pauses as `NEEDS_AUTH`.
3. HTTP 401/403, explicit false, and missing user identity remain paused.
4. Existing discovery and coordinator tests continue to pass.

## Recovery

After deployment, a run already paused in `NEEDS_AUTH` can resume from A. A run
already marked `FAILED` remains terminal and requires a new run.
