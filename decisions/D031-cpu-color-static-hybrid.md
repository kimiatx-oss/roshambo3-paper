# D031 — CPU color starts with a static, cache-aware hybrid

**Date:** 2026-10-05
**Status:** active implementation direction, authorized by the author; production thresholds remain uncalibrated
**Source:** `results/T178/memory/README.md`, `summary.json`, `REVIEW.md`; the author's direction to prioritize ordinary combo and amortize query construction
**Constrains:** T158, T159, T162, T179 and subsequent CPU combo implementation

## Decisions now, not shipping defaults

Select a backend for each target-type color plane once at query setup, jointly
budgeting shape and color. Do not switch representations within trajectories in
the first implementation. Keep forced-backend overrides. D029/D030's anchors,
shape configuration and score semantics remain intact; no default changes yet.

| Backend | Initial implementation | Why retain it |
|---|---|---|
| Analytic | fp32 SIMD, real counts, safe tails; scalar fallback | Sparse planes or poor field locality |
| Node trilinear | AoS value + three stored gradients, four-channel SIMD; fp32 or fp16 nodes | Compact storage with host-dependent conversion/traffic trade |
| Polynomial brick | fp32 coefficients, four-channel SIMD | Nearby repeated accesses can outweigh its larger footprint |

Reuse established GPU spacing/prefilter and coordinate conventions, adapting
explicitly to the CPU frame. Store and interpolate gradients: no first
differences, no differentiation of the interpolated value. Parity means matching
the calculation, not bitwise results. Do not reopen resolution or require a new
fp64-versus-feature-count accuracy campaign. Independent formula/fixture checks
and existing production ranked-output gates still apply.

Start field SIMD across four channels, not eight-target AoS gathers: those
particular gather arms lost on both hosts. Other layouts/grains remain eligible
later if measured in production. Analytic fp32 expf/exp2f and vector polynomial
alternatives are eligible. Polynomial approximations, tail cutoffs, FTZ/DAZ or
reduction changes must be declared/validated under D029 before adoption; do not
silently inherit the probe FP environment or compare only to scalar fp64 exp.

## Evidence and limits

T178 provides reviewed conditional paired **primitive** evidence, not production
approval (D015). Construction was excluded; shape coexistence was a proxy. In
compact one-plane eight-target cases, bricks crossed between two and four query
features; in six-large-field broad-independent stress cases, even half nodes on
roci crossed only between 48 and 64 under the explicitly bounded/FTZ control.
These are not ordinary workload estimates or shipping thresholds. There is no
working-set-independent cutoff of 12 query features.

Half/decoded-fp32 time on a small compact case was approximately 1.025 on roci
and 1.171 on tachi, versus 0.821/0.809 with six large fields and broad accesses.
This changes conversion AND footprint, not conversion alone. Bricks also change
from winning to losing with locality. See the source for intervals, exclusions,
FP modes and clock limitations; do not pool modes or decide from near ties.

## Policy and the meaning of density

Use exact contributing query counts/interaction weights, target real-count/tail
buckets, grid extent/bytes, ISA/cache topology and shape-plus-color footprint.
General-matrix fields are indexed by **target type** and sum contributing query
types with their own widths/heights. An unweighted effective feature count is a
cost proxy, not a replacement for this algebra. Empty canonical planes do no
work; unsupported cases use analytic fallback.

Separate pair-work density from access locality. Numerical nonzero-voxel
fraction is not useful dispatch information for full allocated grids without
zero skipping. Do not scan grids or add sparse-grid construction for this
policy. Allocation bytes are a conservative capacity indicator, not measured
cache residency; roci's separate L3 domains cannot be added into one cache.

T179 samples ordinary trajectories **offline** for distinct cells/cache lines,
step reuse and spatial extent. Test whether cheap query/target geometry and
start-strategy predictors improve on counts/bytes. The initial policy requires
no runtime tracing, trial alignments, or score lookahead. If locality is not
predictable safely, use a conservative estimate or analytic fallback.

T162 fits a small preregistered cost table with a query-wide budget, not six
independent cutoffs that overfill cache. Begin with a **provisional 10% predicted
saving margin** versus analytic; calibrate/freeze on tuning data, never evaluation data.
This is neither a measured optimal margin nor a promised gain. Preserve
pose/step locality and serial mixed-plane execution first. T160 interleaving
and T161 phase-opposed independent SMT are later optimizations, not blockers;
cooperating SMT is outside the first implementation.

## Amortization and execution order

Report alignment and exact-final analytic scoring separately from query setup.
In the large-library limit select on alignment cost. For finite reuse:

`total = setup + build(selected planes) + sum(alignment calls) + final scoring`.

Measure isolated per-backend construction/packing; T178's combined node build
is not that cost. Record evaluation reuse counts as well as database size:
starts, steps and target-plane counts affect amortization. Build only selected
representations on the hybrid path, not all benchmark arms.

T158 analytic production integration and T159 field production integration run
alongside T179 ordinary trajectory characterization; then T162 calibrates the
static hybrid. Bounded execution suits Luna-max for T158/T159/T162 and Luna-xhigh
for T179, with independent Sol review. T157 hard-reference mining and T163/T164
rescore-selection research do not block this work. Compare ordinary mixed-plane
combo with the scalar T156 schedule first; do not claim a converged optimum.

Default adoption still requires forced-arm correctness, general-matrix/empty/
tail tests, ordinary combo ranked checks through repository metrics, separate
rate/accuracy grades, T118 matched populations/host arbitration/affinity,
held-out policy regret and the manual T149 scoring/codegen pre-merge canary.
If qualified timing is unavailable, land correctness/build-gated kernels while
leaving performance/default acceptance open.

## Reopening conditions

Revisit representation/grain when production timings reverse rankings, a matrix
fails its contract, or a new host lies outside calibration. Revisit the static
policy if held-out regret exposes unpredictable locality. Add scheduling only
after an ordinary combo profile identifies opportunity. Reopen resolution for
a demonstrated production retrieval failure attributable to it, not an isolated
stringent fp64 diagnostic.
