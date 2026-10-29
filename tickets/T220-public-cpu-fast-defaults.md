---
id: T220
title: Public CPU fast-route defaults and optional resource safeguards
phase: 2
lane: integration
status: closed
model: sol
reviewer: sol
depends_on: [T219, T216]
priority: highest
artifacts: results/T220/
---

The author requested automatic fast public CPU screening across shape, rescore and
combo, and removal of arbitrary public memory ceilings. FIELD requests should
use existing worker-owned kernels without changing objectives, exact finals,
matrix eligibility or query-cache lifetime. Omitted CPU workers should follow
process affinity; GPU decoding retains its existing default. Explicit worker
options remain authoritative.

Public memory/top-K ceilings become optional (None means no configured cap).
Retain explicit positive-byte safeguards, native overflow checks, bounded
worker-local top-K and memory-estimate statistics. Use the existing native
top-K estimator without allocating a collector to charge actual estimated
storage, not the caller's full maximum allowance, in joint preflight.

Verify all three modes and both ranking levels through api.screen, automatic
CPU affinity, explicit budgets/worker overrides, preflight before query/decode,
query reuse and native estimator/collector agreement. Fresh T149 and independent
review are required before merge. Work/scratch under `<scratch>`; no new benchmark
harness or speculative kernel optimization.

## Outcome (2026-10-10)

Implemented and independently approved: automatic supported fast CPU shape,
rescore and combo facade calls; affinity-based omitted workers; optional public
memory/top-K ceilings; and pure native actual-estimate top-K preflight. Unsupported
implicit requests retain the ordinary route, while explicit worker options remain
strict. Both ranking levels are covered; GPU default routing/count is preserved.
243 affected tests and fresh 14-arm T149 passed. No new timing claim. Verification
and precise resource semantics: `results/T220/public-fast-defaults-20261010/REPORT.md`.
