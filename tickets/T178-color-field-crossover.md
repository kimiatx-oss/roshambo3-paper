---
id: T178
title: Derive and measure the color-plane field crossover on CPU and GPU
phase: 2
lane: research
status: open
model: sol
reviewer: astra
depends_on: [T28, T124, T153, T155, T156]
priority: deferred
branch: ticket/T178-color-field-crossover
worktree: <worktree>
artifacts: results/T178/
---

## Sprint disposition — 2026-10-10

Open, deferred crossover-model qualification; no active agent reservation.
The derivation, amortization model and CPU/GPU experiments remain recorded,
including the independent review's unresolved GPU isolation/timing and
full-pose accuracy qualifications. No rough count bracket becomes a validated
universal threshold, and no missing final review is claimed passed. T159/T217
measure composed CPU implementations; T218's current analytic default does
not require further primitive accuracy exploration. Revisit only if transfer
to a new workload/backend is needed; preserve advisory labels and failed gates.

This is the current queue state; earlier assignments/status statements below
are historical. No build, code change or experiment was run for closeout.

## Historical context

Implementation/evidence checkpoint (2026-10-05): bounded native CPU/GPU
experiment and derivation are in `results/T178/README.md`, with source scripts
under `tickets/T178/`. CPU compares audited fp64 baseline, scalar fp32 expf/
exp2f, available vector libmvec and explicit float8 polynomial. Primary fields
use shipped stored-gradient half4 calculation and fixed spacing, with CPU
software/RGBA brick and sm70 hardware texture. Finite CPU complete-screen
checks confirm build-amortization direction; all gates/intervals and
preliminary alternatives are retained. D015 production timing transfer remains
open. Follow-up amendment 5 now corrects the private GPU
analytic control to shipped reduced exp2f/hoisted prefactor and repeats the
same matched cells; old physical-expf results are preliminary. Corrected
advisory GPU brackets are (16,32] value and (8,16] gradient. Clock/error checks
support conditional comparisons, not complete isolation or a production decision. Ticket stays
claimed pending Astra/fable review;
no main merge or production dispatch policy is authorized by these results.

Independent-review response: `results/T178/REVIEW.md`. Complete native CPU
pose/torque oracle checks and four freshly interleaved finite screens are now
recorded; qualification requires both spatial and full-pose gates. Ell8/m16
field torque fails 5% even though spatial samples pass, so passing counts are
not monotone. Source counts and precision labels corrected; fresh m32 CPU
build/delta uncertainty propagated jointly, other one-build curves explicitly
unresolved. GPU brackets above are now ADVISORY, not qualified: GPU isolation
could not be verified during the runs (pitfall 31). GPU review/clean timing
remain open.

A color field removes the query-feature factor from the analytic double loop,
but interpolation has a fixed cost per library feature. T159 currently ranks
planes by estimated interaction work without a measured break-even threshold.
Its one qualified large-library timing used only two interacting query features
and lost to scalar analytic color; that path also materialized large intermediate
arrays. It does not locate the crossover for an efficient native evaluator.

Derive where the crossover should lie in query atoms/features per plane, then
test that prediction with a small compiled experiment on CPU software/brick
interpolation and GPU hardware interpolation. Separate the once-per-query field
construction cost from alignment cost, yielding both the large-database limit
and finite-database thresholds. This ticket supplies a cost model to T159/T162;
it can run before those tickets close and requires no T157 reference campaign,
hard-case mining, retrieval study, or new optimizer search schedule.

## Scope

### 1. Define the plane and the reuse unit

- Use the frozen T153 color expression and distinguish molecular atoms from
  merged color features. For the canonical diagonal matrix, `m_t` is the number
  of query color features of type `t`. For a general matrix, the field indexed
  by library target type `t` sums every query feature with positive interaction
  width and nonzero height against `t`; `m_t` is that effective contributing
  count. If costs differ by interaction width/type, retain weighted term counts
  rather than pretending that all features have one cost.
- Define `N` as library conformers, `ell_t` as mean library features of target
  type `t` per conformer, and `e` as pose evaluations per conformer reusing the
  same query field. The reuse count is `Q = N * e`, not just `N`: fixed-pose
  rescore has `e = 1`, while combo value/gradient evaluation pays repeatedly
  across starts and steps. Hold the schedule fixed when comparing costs.
- Record grid nodes `G`, spacing, extent, storage, interpolation representation,
  bytes per plane, and fraction `rho` of target features sampled in-domain.
  Selected planes use fields; unselected planes and out-of-domain positions
  use analytic evaluation. State which costs cancel in a mixed comparison.

### 2. Derive the operation counts and time model before timing

Produce a source-backed table for value-only and value-plus-spatial/pose-gradient
evaluation, counting ordinary FLOPs (FMA = 2), exponentials/SFU operations,
loads/stores and bytes, addressing/conversion, and reductions separately:

- Analytic: coordinate transform reuse, squared distance, width/height factors,
  exponential, value accumulation, and gradient accumulation per interacting
  query/library feature pair. Compare the scalar control with the available
  vectorized/device analytic implementation; record width and tail costs.
- CPU software trilinear: eight corner samples and interpolation arithmetic;
  CPU brick/polynomial: packed coefficient fetch and polynomial value/gradient
  evaluation, including brick indexing and decoding. Reuse T124's mechanisms
  or a minimal equivalent compiled implementation. Count the existing 64-node
  Catmull-Rom color evaluator as a sensitivity/control where available.
- GPU hardware trilinear: texture instructions, coordinate conversion, texel
  layout and bytes, and value/gradient channels. Determine whether gradients
  come from interpolated stored derivative channels or extra fetches; hardware
  interpolation of values alone does not produce the required gradient for
  free. Include derivative-channel construction and storage in the build cost.
- Field construction: node evaluations, storage/packing or brick coefficient
  conversion, allocation, and GPU upload/texture creation when paid by the
  deployment. For a direct builder, start from
  `B_t(m_t,G) = B0 + G * (b_store + m_t * b_gaussian) + B_layout/upload`, then
  replace this with the actual builder's operation count if it differs.

Translate counts into a high-level throughput/latency estimate. FLOPs alone
cannot price an exponential, a cache miss, or GPU texture throughput. Show the
predicted range using explicitly sourced or separately calibrated costs for
SIMD/SFU, cache traffic and texture service; label assumptions and calibration
separately from the subsequently observed crossover. Do not count hardware
texture interpolation as zero cost because its arithmetic is offloaded.

Use an explicit model such as the following, with per-evaluation setup terms
`a0`/`f0`, analytic pair cost `c_A`, and in-domain field sample cost `c_I`:

```text
A_A(m) = a0 + ell * m * c_A
A_F(m) = f0 + ell * [rho * c_I + (1-rho) * m * c_A]
Delta(m) = A_A(m) - A_F(m)

T_A(N,m) = Q * A_A(m) + R_A(N)
T_F(N,m) = B(m,G) + Q * A_F(m) + R_F(N)
Q = N * e
```

Here `f0` includes the bounds/dispatch/setup costs outside the sample body;
`R_A`/`R_F` include any non-common reporting, final exact rescore, and launch or
transfer costs. Express those costs explicitly and avoid double counting.
Derive these consequences for each platform/interpolation/objective arm:

- Large-database crossover: solve `Delta(m) > 0`. With constant coefficients
  and `rho > 0`, the continuous threshold is
  `m_inf = [c_I + (f0-a0)/(ell*rho)] / c_A`; report the first winning integer
  feature count as well as the continuous root. Handle empty planes and
  `rho = 0` explicitly.
- Finite database: solve
  `B(m,G) + [R_F(N)-R_A(N)] < N * e * Delta(m)` for both `m_crit(N)` and
  `N_crit(m)`. When reporting costs cancel and `Delta > 0`,
  `N_crit = B/(e*Delta)`. If `Delta <= 0`, field construction amortization
  alone cannot create a win.
- Include the dependence of construction on query count. For fixed geometry
  with `B(m) = B0 + b*m` and common reporting costs, derive
  `m_crit(Q) = [B0 + Q*(f0-a0 + ell*rho*c_I)] /
  [Q*ell*rho*c_A - b]` when the denominator is positive. When it is not,
  no query-count crossover exists under that fixed-coefficient model.
- Increasing query count can change grid extent/cache regime; the expression
  above is conditional on fixed geometry and coefficients. Give estimates
  for realistic extents and state when a piecewise/numerical solution is needed.
  Build cost is once per query/plane per screen, independent of `N`; do not
  rebuild it per batch or per pose evaluation.

### 3. Build and run a small validation experiment

1. Freeze the operation table, predicted crossover ranges, coefficients,
   accuracy checks, and experiment budget before the main crossover sweep.
   Use native compiled hot loops with the same coordinates, target counts,
   pose sequence, outputs, and reduction work in each comparison. Reuse
   T153/T155/T156/T159 code where practical; confirm source/build provenance
   for any unmerged experimental evaluator. Python orchestrates the runs.
2. Begin with one active plane, fixed extent, one representative `ell`, and
   all positions in-domain. Sweep effective query count
   `m = {1,2,4,8,16,32,64}`, then refine near the predicted/observed crossing
   with a bounded additional sweep. Keep query coordinates distinct within a
   fixed domain and preserve library/pose distributions across arms. An empty
   plane is an untimed correctness/control case.
3. Measure value-only and value-plus-gradient separately. On CPU compare
   analytic, software trilinear, and brick/polynomial interpolation; include
   the existing cubic arm if available. On GPU compare matched analytic with
   hardware interpolation. Use available ISA targets on roci/tachi and the
   selected available GPU; stamp the actual device, width and representation.
   Start with one storage/spacing per interpolation arm so this stays a small
   experiment; declare approximation error against the independent reference.
4. Measure construction separately, including field derivatives/layout/upload
   when relevant. Time a repeated alignment loop with the built field reused.
   Report build seconds/query, evaluation seconds/pose and per target feature,
   useful analytic pairs, field sample counts, and actual bytes/operations.
   Eliminate unequal large host allocations and packing from the primitive
   comparison; price any required deployment preparation separately.
5. Predict finite thresholds at `N = {100,1000,10000,100000,1000000}` and
   declared `e` values from measured build and evaluation costs. Directly
   validate totals at a small number of sizes bracketing a predicted
   `N_crit`, building once for each complete simulated screen. Record GPU
   launch/batch occupancy effects; small-N predictions cannot use saturated
   throughput without its fixed costs or a measured size-dependent correction.
6. Check one modest alternate target count and one alternate grid/cache
   footprint or out-of-domain fraction to assess sensitivity. Confirm the
   count convention and arithmetic on the existing ordinary q4/q19 cases;
   controlled synthetic geometry measures computation, not retrieval quality.
   GPU repetitions/tiling must reach steady throughput (pitfall 14) without
   requiring a million unique molecules or a reference-optimum campaign.
7. Keep the initial timed campaign within 30 minutes per selected host/device,
   excluding compilation and waiting for availability. Report a bracket or
   no crossing within the tested range when that is what the data supports.
   Commit any extension to the range/budget before running it.

## Deciding measurement

A reproducible operation-count model and predicted-versus-measured crossover
in effective query features for CPU software, CPU brick, and GPU hardware
interpolation, separately for value-only and value-plus-gradient. Publish
`m_inf`, finite `m_crit(N)`/`N_crit(m,e)`, uncertainty/brackets, build cost, and
evaluation cost in `results/T178/`, with raw timing records and a compact plot
of evaluation time against query count plus finite-database break-even curves.
A measured lack of crossover in the tested range is a valid result.

## Acceptance

- The derivation states units and counts for both construction and alignment,
  handles analytic fallback, repeated evaluations and non-common exact rescore,
  and recovers the large-database limit from the finite model.
- Each requested platform/interpolation arm has a source-backed operation
  count and a measured crossover/bracket or a measured no-crossing result.
  Unsupported hardware or noisy timing leaves that part open.
- Predictions are recorded before the sweep. Compare predicted and observed
  thresholds with paired timing uncertainty; explain material discrepancies
  using measured coefficients or a bounded causal check rather than refitting
  and presenting the fit as an advance prediction.
- Value and gradient outputs pass declared independent T153-derived numerical
  checks, with interpolation error reported. Distinguish the computational
  crossing from an accuracy-qualified crossing if an interpolation arm fails
  the declared color accuracy bar. Use D029 for cross-ISA comparisons.
- The experiment produces a candidate per-plane cost rule, conditional on
  hardware, interpolation, query count, occupancy and reuse. Production subset
  selection and optimizer/retrieval acceptance remain with T159/T162.

## Traps

- **Pitfall 24:** an analytic estimate is a prediction; record it separately
  from measured rates. GPU texture work has a cost despite few visible FLOPs.
- **Pitfalls 8/18:** total query atoms or padded width are not interacting
  feature count. Hold target counts and pose/batch layout fixed when varying
  `m`; a general interaction matrix can combine several query types.
- **Pitfall 11:** expose construction, upload, host setup and exact rescore;
  keep hot alignment time separately visible for large-library amortization.
- **Pitfalls 3/5:** controlled geometry is valid for a cost probe; use the
  independent reference for arithmetic and make no retrieval-quality claim.
- **Pitfall 14 / D015:** reach GPU throughput saturation and price launch
  effects. A primitive crossing is conditional; cache contention with other
  color/shape planes can move the production crossing.
- **D009:** working-set size or hit rate alone does not prove a cache cause.
  Stored derivative-channel interpolation can differ from differentiating the
  value interpolant; declare the method and validate its error.
- Two interacting query features losing in T159 does not establish a universal
  threshold. T28's measured shape crossover is precedent, not a color result.

## Working rules

Use the ticket branch/worktree and the six-section ticket protocol. Assigned
to Sol 6.1 (Codex) at medium reasoning by the author, with Astra/fable reviewing the
model and measurement. This is a bounded derivation and implementation task. Read the
standing decisions, T153 color contract, T28 GPU interpolation findings,
T124 CPU field work, T158 analytic controls, and T159 mixed-field code/evidence.

Commit the derivation, calibration definitions and benchmark scripts before
quoted runs. Use T118 CPU arbitration and the established per-device GPU lock,
taking the GPU lock before context creation; record load, achieved clocks,
toolchain/ISA, source/binary/input hashes, repeats and timing regime. Follow
D007/D023 when comparing timings and D011 for bounded progress monitoring.
Apply the manual T149 pre-merge canary if implementation changes affect CPU
scoring or code generation. Share corpus paths and preserve other agents'
files. Leave this ticket open until the deciding artifacts have been reviewed.

Reviewed partial evidence: `results/T178/README.md` and the two-host CPU
precision/layout/locality follow-up in `results/T178/memory/README.md`.
Independent reviews approve research-artifact merge, not production dispatch
or ticket closure. The CPU follow-up separates alignment from construction,
includes native fp32 and half nodes, and shows why working set/locality must
enter the per-plane speed rule. See `results/T178/memory/REVIEW.md` for scope
and exclusions. Keep this ticket claimed/open; production transfer is T159/T162.
