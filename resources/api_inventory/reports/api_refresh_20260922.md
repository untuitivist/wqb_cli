# API inventory refresh 2026-09-22

Catalog: 109 -> 127 paths; 131 OPTIONS path probes.

Allow methods are advertised capabilities, not proof of account permission or a successful live mutation. An OPTIONS 405 is recorded even if Allow advertises OPTIONS.

New option snapshots contain schema shape only; account-specific choices, cookies, headers and response data are excluded.

Current inventory plus current frontend route references were checked. Unresolved resource IDs and routes absent from those sources are not claimed as exhaustively verified.

## Added paths

- `/agreements/privacy-policy`: Privacy policy agreement resource.
- `/agreements/referral-agreement`: Referral agreement resource.
- `/alphas/{alpha_id}/recordsets/turnover`: Alpha turnover recordset.
- `/data-fields/{field_id}/visualize`: Request a field visualization. Frontend uses POST with instrumentType, region, delay and universe query parameters; response format is not yet verified.
- `/messages/announcements`: Announcement collection and read-state operations.
- `/messages/notifications`: Notification collection and read-state operations.
- `/users/self/activities/submissions`: Current user's submission activity history.
- `/users/self/alphas/{alpha_id}/before-and-after-performance`: Before-and-after performance for an Alpha in the current user's collection.
- `/users/self/streak`: Current user's activity streak, current-day activity and history.
- `/users/self/tags`: Current user's tags, lists, categories and colors.
- `/users/{user_id}/activities/{activity_name}`: Named user activity history, including base-payment, other-payment, referrals, simulations and submissions.
- `/users/{user_id}/consultant`: Consultant performance resource; account-role restrictions apply.
- `/users/{user_id}/consultant/summary`: User-scoped consultant performance summary.
- `/users/{user_id}/osmosis/scale-points`: Start asynchronous Osmosis point scaling; frontend uses POST with no JSON body.
- `/users/{user_id}/osmosis/scale-points/ALL`: Osmosis point-scaling progress. Retry-After means processing; 204 without Retry-After is a normal terminal response.
- `/users/{user_id}/osmosis/summary`: User Osmosis allocation summary.
- `/users/{user_id}/profile`: User public profile resource.
- `/users/{user_id}/researcher`: Researcher performance resource; account-role restrictions apply.

## Status counts

```json
{
  "405": 33,
  "SKIPPED_NO_OBSERVED_ID": 8,
  "200": 63,
  "404": 21,
  "400": 3,
  "500": 3
}
```
