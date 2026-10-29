---
id: T214
title: Add a lean canonical identity-interaction CPU color kernel
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T212]
priority: highest
artifacts: results/T214/
---

## Sprint closeout — 2026-10-10

Closed for the independently reviewed canonical identity-interaction helper,
fallback/census correction and subsequent T218 default promotion. See
canonical composition review (`results/T218/CANONICAL_COMPOSITION_INDEPENDENT_REVIEW_20261010.md`)
and composed public review (`results/T218/PUBLIC_COMPOSITION_INDEPENDENT_REVIEW_20261010.md`).
T220 preserves automatic public routing; noncanonical interactions retain the
general path. The earlier default-OFF/handoff text is historical.
Paired composed rates do not establish eliminated pair counts or instruction
savings by themselves. Remaining useful-work-normalized instruction/pair
attribution is explicitly optional T221 work; it is not a missing production
correctness gate or a claim that those counters were already collected.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

The overwhelmingly common interaction is equal-type only. The author authorized
aggressive specialization while leaving rare general matrices unoptimized.
Current CPU canonical scoring already visits same-type pairs; remaining
general evaluator machinery is the opportunity, not an assumed 49-to-6 pair
reduction. Recommended 6-Luna-max (Haiku), independent 6-Sol-medium review.

## Scope

1. Detect canonicality once in immutable query preparation using the existing
   Matrix predicate: active R entries all 1 and P diagonal 1/off-diagonal 0.
   This is not R=identity; reserved shape/type 0 conventions remain intact.
   Classify actual matrix contents, not feature enum or a caller assertion.
2. Build a distinct canonical analytic evaluator, retaining strategy16 and
   shared FP32 pose. Resolve diagonal plane descriptors, invariant coefficient/
   reduced decay, query coordinates/counts and support eligibility outside the
   iteration/pair loops where safe. Remove irrelevant general interaction and
   field-policy machinery from this analytic-only path. Skip empty planes.
3. Preserve pose-dependent safety/fallback for exceptional inputs, but isolate
   it from the ordinary bounded fast path. Keep the existing general matrix
   implementation and exact scorer untouched; noncanonical inputs route there.
   No general-matrix optimization or silent matrix approximation.
4. Start with unchanged exp approximation and gradient formula so the first
   benchmark isolates specialization. Use direct broadcasts/reuse for the
   four start lanes where beneficial; avoid repacking invariant query data per
   iteration. Provide narrow helper interfaces for T215/T216, not duplicate
   optimizer/scheduler implementations.

## Deciding measurement

Paired whole-combo throughput versus the same baseline, instruction count and
issued/useful pair counts. Explicitly identify pairs eliminated (if any) versus
instructions/control/setup eliminated. Confirm the promising candidate at 24P
on cloud using the shared short budget.

## Acceptance

Small-panel top-K and exact-final gates from the shared contract; wrong/near-
canonical matrices correctly fallback, general regressions unchanged, tails/
empty planes/shared-pose/thread tests pass. Fresh exact-candidate T149 and
independent review. Retain an isolated forced baseline for causal comparison;
T218 selects the composed production default.

## Traps

Pitfalls 5/18: do not infer correctness from two copies of the same kernel or
claim removed off-diagonal work that the baseline already skipped. Canonical
classification must respect both widths and coefficients. Do not erase required
dynamic finite/range checks on the theory all user input is ordinary.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Independent branch;
prefer a dedicated canonical helper TU and minimal hooks. T215/T216 are
parallel, not prerequisites; coordinate signatures rather than sibling edits.

## Reviewed implementation handoff (2026-10-10)

Source `885f2713`, report-only `729842d7`, independent review `7db8158e`:
canonical helper and mixed safe/fallback-lane statistics correction passed
fresh eight-arm T149 and focused correctness. A clean canonical grain-16
resident single-core comparison gave 0.389060s baseline / 0.360582s candidate
(+7.90% throughput) with identical score hashes. This is exploratory, with
T118 refusal for one warmup/five pairs; no full 24P result was obtained.

T218 incorporated the reviewed helper through source `e3256ba9` with an
explicit default-OFF canonical kernel selector and shared compile-time
raw/baseline and factoring seams. This avoids silently changing defaults or
dropping T215/T216 options. Composed public timing remains the qualification
gate; this ticket does not claim a production speed/default promotion.
