---
id: T217
title: Prepare color fields once and dispatch a static per-query plane hybrid
phase: 2
lane: kernel
status: open
model: luna
reviewer: sol
depends_on: [T212]
priority: deferred
artifacts: results/T217/
---

## Sprint disposition — 2026-10-10

Open, deferred fixed-schedule/selective-field follow-up; no active reservation.
Prepared/reused fields and setup-time selection are integrated and reviewed.
The bounded trilinear/brick experiment below lost to composed analytic color
with one-time build excluded; T218's default threshold table remains empty.
That negative is a completed hypothesis, not a mandate to keep sweeping.
Remaining scope is new fixed plane scheduling (Scope 4) and broader count/
locality calibration if a promising query class appears. T162 owns broad
held-out policy qualification. No universal cutoff or new run is authorized.

This is the current queue state; earlier assignments/status statements below
are historical. No build, code change or experiment was run for closeout.

## Historical context

The author requested selective fields above the measured query-plane crossover, with
construction reused and backend selection ABOVE the optimizer loop. T178
derived/tested primitive crossings; T159's bounded integrated cells did not
show a field win even excluding construction. Neither implies a universal
12-feature cutoff. Build the static reusable policy and validate it on both
sides of the relevant count boundary, including genuinely dense query planes.
Recommended 6-Luna-max (Haiku), independent 6-Sol-medium review.

## Scope

1. Read T178 derivation/review, T159 low-core timing and T179 locality/T162
   readiness. Reuse existing FP32 node/trilinear and FP32 brick primitives;
   stored value/gradient interpolation, not finite-difference gradients or a
   new resolution study. FP16 is not required on CPU. Start canonical-only;
   general matrices remain existing analytic fallback.
2. In query preparation, classify each active plane once by query feature
   count and a small calibrated per-representation cost table, constrained by
   joint shape+color memory/cache budget. Begin with a count cutoff, adding
   only byte/representation guardrails supported by measurements. No voxel
   scan, online timing oracle, trial alignments or per-iteration policy solver.
3. Build only selected fields once per query/plane/resolved geometry, before
   the library scan. Extend T212's bounded query-generation binding/lifetime/
   memory accounting to include color-field policy/threshold/precision/grid
   and interaction inputs. Hits reuse actual handles across Engine runs;
   query/policy/build changes invalidate them. No per-block/start/step builds.
4. Select a hybrid evaluator/schedule BEFORE optimizer iteration: fixed lists
   of analytic and field planes, fixed representation and immutable handles.
   No repeatedly asking feature counts/crossover or whole-plane eligibility
   at every turn. Dynamic cell bounds remain necessary: define safe analytic
   sample fallback outside the grid, counted separately, without changing the
   static policy or silently clamping/discarding contributions.
5. Compare analytic, forced trilinear, forced brick and static hybrid for a
   small source-count bracket around the measured boundary with actual field
   shape enabled. Include one/few selected planes; do not build all six and
   price the unused allocation. Calibrate against the currently available
   analytic baseline, then hand off cost measurements for T218's faster composed
   analytic baseline (which can move the cutoff upward).
6. Separate field build/pack cost from alignment rate. Report large-library
   cutoff and finite-N estimate B/(A-F) where A>F, in clearly consistent units;
   A<=F means no amortization break-even. Do not charge B on each molecule.

## Deciding measurement

Alignment-only whole-combo rates and per-plane actual dispatch/fallback/build
census; bounded top-K validation and separately measured build/memory costs.
Static hybrid must beat a same-session analytic baseline in a documented dense
class before default promotion. An always-analytic outcome is legitimate.

## Acceptance

Tests prove fixed policy selection, zero warm rebuilds, cache hit/invalidation,
budget refusals, safe out-of-grid handling and unchanged exact final scoring.
Shared small ranking gate; no stringent all-feature FP64 interpolation campaign.
Fresh exact-candidate T149 and independent review. Update T162 with the bounded
policy handoff, without declaring its historical full calibration complete.

## Traps

Pitfalls 8/11/18: same corpus/shape path and complete scan boundary. Construction
is O(1) in library size and cannot decide a small-panel alignment comparison.
Primitive crossover is not a universal integrated cutoff; faster analytic
and additional fields change it. Fixed policy does not remove dynamic spatial
boundary safety. A losing sampled dense class must not trigger an endless sweep.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Own a static color-field
policy helper and bounded query-cache integration, not shape sampler rewrites.
Coordinate small T212 context extension with the orchestrator. T214–T216 do not block the
initial experiment; T218 refreshes the final composed cutoff.

## Reviewed partial integration (2026-10-10)

Static per-query policy selection and native prepared-handle cache reuse are
merged as opt-ins, with an empty default threshold table (all analytic).
Corrected source `108ffb4a` recognizes exact active R=ones/P=identity, ignoring
reserved type 0. Focused tests cover actual selected fields, warm/block reuse,
policy invalidation and grain-16 out-of-grid analytic equality. Legacy explicit
FP16 code 2 remains compatible but outside this policy's FP32 qualification.

Combined T217/T218 source `75e18e1f` passed targeted regressions and fresh
11-arm T149, report-only head `ebf2d3ec`, independently reviewed in `0df1ddb4`.
Ordinary canary arms do not exercise the opt-in field policy; focused tests do.

This is not complete Scope 4 or performance promotion: grain 16 retains its
existing pose-dependent whole-plane/lane bounds preflight and coarse fallback
census. Static count/cost policy decisions are outside the optimizer, but no
new fixed plane schedule or measured field cutoff is claimed. Alignment-only
trilinear/brick/hybrid comparisons, construction amortization and cutoff
refresh against the composed analytic kernel remain open.

## Reviewed bounded field decision (2026-10-10)

Runner review `efe44b82`, initial evidence review `633d86e4` and corrected-lock
review `c9fa4842` approve the fixed top-two-plane experiment against composed
canonical/raw/factored analytic color. Corrected-lock source `8697db5e`,
report-only head `a81f60fe`, report SHA256 `d66c4007dab9c356f60ee1358dc9f62c7dfe31a929e119007722285fb38aead0`:
warm four-query/16,384-pair medians were 0.889413s analytic versus 1.601301s
FP32 trilinear, and 0.891408s analytic versus 1.477100s FP32 brick. Field
throughput is lower by 44.46% and 39.65%; all four sampled query classes lose.
Both representations pass the frozen tune and held-out ranking gates.

One-time build/pack costs 0.039855s/0.072331s are excluded from warm timings.
Neither fixed plan has a positive finite-N break-even because its warm slope
already loses. Any selected field currently disables the dedicated canonical
helper for the native call, so these are real composed hybrid costs, not a
pure interpolation primitive comparison. Aggregate out-of-grid preflight is
coarse; no universal count threshold follows from this four-query experiment.

The corrected repeat records the specified host-qualified project CPU lock,
CPU0 affinity, clear process snapshots and matching native source/DSO hashes.
The first run's default lock-path caveat remains preserved separately. These
are exploratory direct score_pairs timings, not official T118 decision-grade
or public full-library rates. Keep the default threshold table empty: analytic
color wins these bounded field hypotheses. No additional field sweep is
required for T218's current analytic policy. T217 remains partial for Scope 4
fixed scheduling and broader per-plane calibration; no default promotion or
historical full ranking qualification is claimed.
