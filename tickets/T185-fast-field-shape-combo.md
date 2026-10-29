---
id: T185
title: Integrate scalar and vectorized shape-field evaluators into CPU combo
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T122, T124, T146, T153, T156, T181]
priority: highest
branch: ticket/T185-fast-field-shape-combo
worktree: <worktree>
artifacts: results/T185/
---

## Sprint closeout — 2026-10-10

Closed for the reviewed scalar, paired-channel and pipelined FP32 shape-field
adapters: integration review in `results/T184/INTEGRATION_REVIEW.md`.
Their production integration continued through T193/T194 and T218/T220;
stored gradients, shared FP32 pose and retained query contexts remain the
contract. The separate original fixed-pose diagnostic timing and original-source
Roci matrix were not completed and are explicitly retired as superseded by
later end-to-end comparisons. This closure does not infer their individual
speedups from composed public throughput or reopen grid-resolution research.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

## Reviewed partial merge (2026-10-07)

Scalar, paired-channel and pipelined FP32 shape-field adapters are integrated
with T184's common combo optimizer. Independent source/protocol and final
Tachi full-combo evidence reviews passed, as did exact-source T149 on
`82284fd3`; report-only follow-up is `80190541`. The diagnostic's native
check-only fixture and observed-count tests pass, but its separate qualified
timing campaign has not run. Qualified Roci full-combo timing also remains
open. No default or ranked-production promotion. See
`results/T184/INTEGRATION_REVIEW.md`; preserve explicit spacing, stored-gradient
sampling and prepared-query reuse. Continue remaining measurements without
reopening resolution/precision research.

## Original context

The author authorized fast shape+analytic-color combo integration 2026-10-06.
Current combo uses scalar analytic shape; T124 already supplies scalar shape
field sampling and AVX2 paired-channel/blocked/pipelined samplers. Adapt those
evaluators, not their shape-only optimizers, to T184's shared combo loop.
Develop in parallel from main `a75ce6b6`, with a committed evaluator handoff.
T184/T185 are parallel implementation siblings, not closed-ticket blockers for
each other. Luna-max executes with independent Sol-medium review; no defaults.

## Scope

1. In field-only new cpp/hpp files provide query-scoped shape-field preparation,
   scalar field gradient evaluation, and vector field evaluators. Reuse existing
   T124 build/sample code, four stored prefiltered channels, coordinate and
   gradient conversions, established geometry and bounds behavior. No first
   differences, derivative-of-interpolant replacement, resolution research or
   new accuracy campaign. Use the reviewed shape spacing policy (T137/current
   shape path), not color's hardcoded grid or a freshly guessed spacing.
2. First scalar FP32 field and existing paired-channel SIMD (two samples times
   four channels); then existing register-resident/pipelined atom sampler if
   genuinely distinct. FP32 is primary to avoid half conversion confounding;
   no fp16/brick/layout sweep required now. Stamp actual sample/atom/channel
   grain, width and representation, not just module capability. Bounds/all-in
   knobs must be honored or rejected; no false path labels.
3. Return reduced shape overlap and descent gradient compatible with scalar
   get_gradient(gnorm=1) for combo weighting. Validate sign/torque/coordinate
   scaling independently; existing shape-only Tanimoto normalization must not
   be applied twice. Do not own/rewrite optimizer loops. Support independent
   poses from color11 eight-pair and color16 two-pair/four-start mappings.
4. Own prepared shape handles with correct query/count/frame/geometry snapshot
   validation, safe lifetime and read-only reuse. Build selected representation
   once per query outside primary timed score calls; do not rebuild fields per
   alignment. Isolated build/pack/bytes and finite reuse estimates remain
   separate. Never construct unused benchmark representations in deployment.
5. Permanent independent value/stored-gradient fixtures, boundary/halo,
   poison/tails, empty/mixed query pairs and fallback/guard tests. Exact scalar
   shape+color per-start/final scoring stays in T184 shared optimizer. Field
   trajectories may differ; report normalized score/rank/pose deltas, not
   copied near-bitwise analytic trajectory gates. Existing ranked acceptance
   still applies before any production promotion.
6. Agree early on committed shape-evaluator seam with T184. Do not touch its
   color_scalar.cpp/publicwrapper/CMake without explicit committed handoff;
   provide field files/tests independently first. T184 owns final integration.
   Publish native correctness probe and preparation/evaluation metadata so
   both arms can be checked without a second optimizer or Python timed loop.
7. Participate in T184 bounded joint six-cell matrix: scalar field, paired-
   channel vector field and pipelined/vector field with analytic color11/16,
   compared to scalar/vector analytic shape in the same sessions on both hosts.
   Shape construction excluded from primary rates. No color field comparisons
   or exhaustive resolution/precision/SMT study in this ticket.

## Deciding measurement

Qualified matched full combo throughput and independent fixed-pose companion
for scalar/vector shape field with vector analytic color. Attribute setup,
field sampling, shape/color weighting and exact final costs separately; native
instrumented phases are not throughput and are never subtracted from rates.

## Acceptance

Supported paths truly execute with stamps/census and permanent correctness;
prepared query reuse validated; source/protocol and final evidence Sol reviewed;
T118 lock/quiet/affinity/source/build/clock/cwd/repeat checks, shared populations;
fresh manual T149 on exact final integrated source, not either parent's older
canary. No shipping-default or unmeasured retrieval/field crossover claim.

## Traps

Pitfalls5/8/11/18: GPU conventions are not independent algebra proof, matched
inputs, full optimizer rates, shape-only wins cannot be multiplied by color
wins. Rebuilding fields in a small-database call unfairly charges construction;
store/interpolate gradients and keep large-DB vs finite-use costs separate.
Do not count T124 channel SIMD as eight independent trajectories.

## Working rules

Isolated worktree/private verified extension, shared read-only
datasets/durable scratch, no shared venv or sibling edits. Read policies and
T124/T137 before implementation. Coordinate host build/test/timing windows
with T184, low-parallel builds2, T118 arbitration for quoted measurements.
Commit/push handoffs early and return clean source candidates to the
orchestrator for independent review. Routine scoped steps do not need another
approval. Stop expansions outside this bounded port/matrix.
