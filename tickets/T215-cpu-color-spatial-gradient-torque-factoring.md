---
id: T215
title: Accumulate color spatial force before forming per-feature torque
phase: 2
lane: kernel
status: closed
model: sol
reviewer: sol
depends_on: [T212]
priority: highest
artifacts: results/T215/
---

## Sprint closeout — 2026-10-10

Closed for reviewed force/torque factoring, bounded ranking gates and its
subsequent composition/default promotion under T218. Preserve the limitations
in the independent review (`results/T215/FINAL-REVIEW-20261010.md`), including
conformer-K versus attached molecule IDs and the exploratory full-scan budget.
This is an explicit scope revision: useful-work-normalized instruction counts
and source-plane-count savings attribution were not measured and move to
optional T221. The old "keep open" instruction applied to that broader scope;
it is not retroactively satisfied by elapsed time. Current composed public
validation belongs to T218/T220; exact finals and general fallback remain.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

The hot AVX2 pair loop forms three torque cross-products for every interacting
feature pair. For a fixed transformed target feature its moment arm is constant
over all query sources. The author authorized factoring redundant work with bounded
top-K validation, not a requirement for old-trajectory bit identity.
Recommended 6.1-Sol-medium (Opus), independent 6-Sol-medium review.

## Scope

1. Derive the evaluator's actual reduced-frame signs/scales. For target j,
   r_j=b'_j-t and pair translation descent f_ij=-w*v_ij*(a_i-b'_j).
   Existing rotational descent is 2*r_j cross f_ij. Therefore accumulate
   f_j=sum_i f_ij and form 2*r_j cross f_j once per target feature, with value
   accumulated alongside. Confirm from source and small finite differences;
   do not copy an unverified physical-frame scale.
2. Implement a canonical candidate that removes per-pair torque arithmetic
   and repeated moment-arm computation. Choose target-outer traversal or
   small worker-local target accumulators based on registers/load cost; test
   at most these two purposeful layouts. Preserve shared pose, masks, four
   starts, final exact scoring and existing fallback. Keep general path alone.
3. Account for changed summation order, accumulator dependencies and possible
   spills. Do not bury this candidate inside a simultaneous exp change.
   Publish an independently callable factoring helper/patch for T214/T218.

## Deciding measurement

Useful-work-normalized instructions and paired full-combo throughput, followed
by the bounded exact-final top-K panel. Report savings as functions of source
plane count: a one-source plane cannot amortize the hoist like a dense plane.

## Acceptance

Tiny fixed-pose gradient/oracle checks plus shared bounded Recall@10/@100 and
exact-final contracts. Intermediate FP32 bit differences are allowed; no huge
accuracy campaign or many correctness repeats. General fallback untouched.
Fresh exact-candidate T149, independent review and measured whole-call benefit
or a reproducible negative conclusion.

## Traps

Factoring changes numerical association; T149 only checks same-candidate
build stability. Cross-product order/sign and reduced translation units matter.
More scratch, a changed loop order or spills can negate the FLOP saving.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Start independently
from current retained kernel; do not wait for T214. Own new factoring helpers,
tests and narrow evaluator hooks on your own branch, not sibling files.

## Partial integration (2026-10-10)

The independently reviewed opt-in implementation is integrated; the production
default is unchanged. Matched canonical full scans improve throughput 5.52%
(241,086 to 254,401 conformers/s); the dense resident single-core probe gains
10.01%. Tiny gradient checks, bounded tune/held-out ranking checks and fresh
exact-source T149 pass. See
final review (`results/T215/FINAL-REVIEW-20261010.md`) and
cloud report (`results/T215/cloud_20261009/README.md`).

Keep this ticket open for useful-work-normalized instruction counts and
source-plane-count savings attribution. Full-scan K100 validation is conformer
membership with attached molecule IDs, not independent molecule top100; proper
molecule retention was checked on the small all-row panel at cutoff 41.
T218 owns composed measurement and default promotion.
