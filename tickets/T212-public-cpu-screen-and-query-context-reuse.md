---
id: T212
title: Expose fast CPU screening and retain immutable query contexts across runs
phase: 2
lane: implementation
status: closed
model: sol
reviewer: sol
depends_on: [T167, T211]
priority: highest
artifacts: results/T212/
---

## Request

Make the public screening API reach the retained fast CPU route, and stop
rebuilding query/field contexts across repeated runs. This precedes further
analytic-color optimization. The existing worker-owned Engine route is the
implementation to reuse, not a new screening pipeline.

## Outcome

Implemented and reviewed. `screen(..., backend="cpu")` reaches supported
combo workers without manual Source/Sink construction; a caller-owned
`engine=` retains a bounded query-context generation across calls. Ordinary
CPU conformer requests use HostTopK without CUDA allocation; ordinary CPU
molecule requests explicitly refuse, while combo supports both levels.
Library-self cache remains Source-bound; no implicit global or Source cache.
234 targeted tests passed, including 23 facade/session tests, and the fresh
exact-candidate T149 passed all eight arms. Usage and evidence:
`results/T212/README.md`, `results/T212/tests.log`, and the linked independent
review. This closes the bounded request, not full T167 qualification.

## Scope and contract

- Expose explicit backend selection and a reusable Engine/session through
  `api.screen`. Construct the untiled source required by CPU workers; preserve
  CUDA defaults, caller configuration, ranking levels and existing refusals.
  Supported CPU combo requests should reach the retained worker route without
  manually assembling a Source/Sink. Do not silently turn shape or rescore
  requests into combo, or promise unsupported modes are accelerated.
- Retain immutable shape/shared-pose query handles on a reusable Engine across
  runs. Bind to query contents/counts/types/R/P, backend/native build identity,
  shape implementation/grain/width and field geometry. Query mutation and
  relevant policy/build changes invalidate reuse. No unbounded global cache.
- Bound retained generations and account their memory against each run's
  budget. Close and failed/canceled runs clear state. Cache statistics must
  distinguish new construction from hits and not recount old self work.
- Test public API translation, actual native parity, repeated-run reuse,
  invalidation, memory refusal and lifecycle cleanup. Document lifetime and
  supported usage, including current legacy-volume precision caveats.

## Working rules

Follow tickets/CONVENTIONS.md. Isolated implementation branch; independent
review, then fresh exact-candidate T149 for scoring dispatch changes. No new
native kernel, benchmark framework, corpus rewrite or performance campaign.
Do not modify or close the independent T211 result archive work. No GitHub
pushes. Full T167 mode/default qualification remains
open beyond this bounded public-route tranche.
