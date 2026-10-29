---
id: T184
title: Integrate analytic SIMD shape grains into CPU combo with trajectory-lane color
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T122, T124, T146, T153, T156, T181]
priority: highest
branch: ticket/T184-fast-analytic-shape-combo
worktree: <worktree>
artifacts: results/T184/
---

## Sprint closeout — 2026-10-10

Closed for the reviewed analytic shape-grain integration and bounded full-combo
comparison: integration review in `results/T184/INTEGRATION_REVIEW.md`.
T185, mandatory shared-pose adoption T193, retained-grain cleanup T194 and
public composition T218 supersede this experimental integration. Current
default uses field shape with analytic color; this is not a new analytic-shape
promotion. Original Roci and separately timed fixed-pose companion requests
are retired, not claimed measured. Reopen analytic shape only with a new
workload or profiling hypothesis; preserve the existing experimental controls.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

## Reviewed partial merge (2026-10-07)

Implementation and the six-cell Tachi full-combo campaign are merged as
experimental opt-in paths. Source/protocol candidate `52036bc0` received
independent Sol approval; results `82284fd3` and the exact-source T149 report
`80190541` received independent final evidence approval. See
`results/T184/INTEGRATION_REVIEW.md` for scope, rates and provenance.
Shipping defaults are unchanged. Remaining work is qualified Roci timing and
the separately timed T185 fixed-pose companion; neither is represented as done.
No production/ranked-retrieval promotion is implied. Resume from the merged
kernel, coordinating host reservations; retain source/protocol review gates.

## Original context

Authorized by the author on 2026-10-06: integrate scalar field, vector analytic,
and vector field shape into full combo, compare a few shape grains, and use
vector analytic color at ordinary eight-pair or two-pair/four-start grain.
Existing combo rates use scalar analytic shape; they do not measure the fast
shape implementations from T122/T124. T182's reviewed partial merge provides
color grain16 as a comparison arm; its Roci timing gate is not a prerequisite.
Baseline is main `a75ce6b6` (kernel source identical to reviewed T182 `fe8a8e50`).
Luna-max implements, independent Sol-medium reviews. No shipping-default change.

## Scope

1. Own the shared optimizer/public API integration. Expose explicit combo shape
   backend/grain/width controls and truthful stamps; legacy unspecified calls
   remain scalar analytic. Separate shape controls from `color_grain`; do not
   silently reinterpret old inert kwargs or the global selected-ISA stamp.
   Publish a committed fixed-pose/batch shape evaluator interface to T185 early,
   including query-scoped preparation, lifetime, pose frame, output and fallback.
2. Reuse T122 analytic evaluators for query-atom SIMD and library-atom SIMD;
   adapt the conformer-grain inner evaluator to return per-trajectory overlap
   and gradients without owning a second optimizer loop. Start with AVX2 width8
   on both hosts. No mandatory new AVX512/mixed-WA/SSE sweep. Reuse established
   exp policy and real-count packing/guards; declare/stamp FP/reduction changes.
3. Keep one combo weighting/update loop. A shape evaluator returns reduced
   S_AB and the same descent-gradient contract as get_gradient(gnorm=1), with
   correct torque, translation scale and no duplicate normalization. Color
   mixing, manifold update, starts/steps and learning rates remain unchanged.
   Shape atom-grain calls may evaluate one trajectory at a time; trajectory
   grain evaluates independent poses in a batch. Do not use a shape-only
   optimized search then color-rescore and label it combo optimization.
4. Color choices are grain11 (eight pairs, starts sequential) and grain16
   (two pairs times four independent starts). Do not use slower compact grain17
   or color fields in the primary matrix. Analytic color polynomial/guards and
   exact scalar fallback stay fixed. Batch shape must accept both pose mappings,
   arbitrary pair IDs/queries and tails, or explicitly refuse unsupported
   combinations; never silently fall back while quoting vector-path rates.
5. Exact scalar shape+color final scoring for every start and winning pose,
   deterministic best-start ties, independent optimizer/cache/lane state, and
   caller output order. Preserve T182 nonstandard-start fallback and tested
   masks. Independent fixed-pose oracle checks values/torque/translation;
   permanent tests cover mixed queries, general color matrices, real-count
   atom tails, odd pair tails, empty segments and unsupported inputs.
6. Integrate T185's scalar/vector field adapters through the committed seam.
   T185 owns field-only files/tests; agree before cherry-picking shared changes.
   Prepared query shape fields are built once outside all timed alignment
   calls and reused. Report construction/packing/bytes and finite reuse separately.
7. Preregister one bounded joint comparison with T185: scalar analytic shape
   anchor, query-atom/library-atom/trajectory analytic shape, scalar field,
   paired-channel vector field and existing pipelined/vector field where
   distinct. Cross each supported arm with color11/16. Start existing six cells
   groups3/5/7 canonical/general,128 pairs,4starts25stepsmix.5,one core,3warmups
   and11rotated repeats. Use same-session baselines, paired CIs and host floor.
   Do not multiply historical shape/color speedups. No new convergence mining.

## Deciding measurement

Qualified whole-combo throughput on Roci/Tachi for each shape backend/grain and
color trajectory mapping, with exact-final cost, setup and gradient attribution
separately identified. Report true shape evaluator selected, useful/issued
terms, scalar fallbacks and paired uncertainty. A bounded negative is valid.

## Acceptance

Independent T153/D029 fixed-pose/ranked checks; fields preserve own-pose exact
rescore and report trajectory/rank deltas without requiring analytic trajectory
identity or claiming retrieval equivalence from one-query timing panels.
Correctness outside timing; clean source/private Release extension stamps,
T118 lock/quiet/affinity/correct cwd/repeat metadata; source/protocol review
before rates, evidence review before merge, fresh exact-source T149 including
after integration. Preserve existing noinline field-state boundaries; isolate
new shape adapters/instantiations in separate TUs instead of growing giant
dispatch bodies. No new flags, defaults or broad arithmetic-policy changes.

## Traps

Pitfalls5/8/11/16: independent oracle, matching work/populations, full optimizer
rates and stable ties. ISA availability does not identify the hot shape grain.
Fields remove analytic pair terms; count samples and invariant schedules rather
than demanding identical pair-work counters. T136/T149 code-size cliffs remain
real. No queries/corpora copied, shared venv edits or sibling worktree changes.

## Working rules

Dedicated worktree, private low-parallel builds (2), read-only
corpora, durable scratch. Read conventions/D029/D030/D031/numeric/metrics policy.
Own color_scalar.cpp/cpu.py/build integration; T185 owns separate field adapter
and tests. Commit/push interface early; notify the orchestrator/T185 before host work
and serialize timed windows. Routine in-scope build/test/review fixes and
qualified runs need no new approval.
