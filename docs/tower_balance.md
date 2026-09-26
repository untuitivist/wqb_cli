# Optional Delay 1 tower balancing

Set manifest `metadata.tower_balance.enabled` to `true` to balance Region ×
Category. Without it the existing random Region/Delay/type selection is unchanged.
Candidate `metadata.category` accepts a category ID, an object with `id`, or an
imported JSON-encoded object. No new schema migration is needed.

The policy selects the least-dispatched eligible tower, randomizing ties, then
randomly fills a compatible batch from that tower. Regular batches contain up to
10 expressions; ALL and Super retain their existing single-expression limits.
Counters count expressions allocated to batches, including retries, rather than
batches, accepted requests, completed results, or successes. Counters live in
`metadata.tower_balance.dispatch_counts` and update in the same transaction as
batch creation, surviving worker restarts. A new policy starts from zero, without
attempting to compensate for historical imbalance.

Existing retry precedence, compatibility, quota waits, not-before times and the
no-resend default remain in force. Balance is approximate within a batch size and
only between towers with eligible inventory at that time. Delay 0 and CHN/CN are
excluded; uncategorized items remain stored but do not dispatch in this mode.
AMR and ALL are eligible with their actual category metadata. The policy does not
invent fields, reclassify categories, expand templates, delete work or submit Alphas.
An empty eligible set cannot meet coverage targets; add economically appropriate
templates with verified fields instead of forcing unrelated data into templates.
