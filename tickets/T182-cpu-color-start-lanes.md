---
id: T182
title: Compare two conformer pairs times four independent SIMD starts for CPU color
phase: 2
lane: kernel
status: closed
model: luna
reviewer: sol
depends_on: [T146, T153, T154, T156, T181]
priority: high
branch: ticket/T182-color-start-lanes
worktree: <worktree>
artifacts: results/T182/
---

## Sprint closeout — 2026-10-10

Closed for the reviewed start-per-lane implementation and bounded Tachi
comparison: integration review in `results/T182/INTEGRATION_REVIEW.md`.
Grain16 denotes two independent conformer pairs times four independent
starts, not feature cooperation. Later T194/T198 and T218/T220 retain and
qualify the production route. Compact grain17's negative result is preserved.
Original-source Roci host validation was not completed by that review and is
retired as superseded, not retroactively claimed satisfied by cloud results
on a different binary. No additional old-source host rerun is required.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

Partial experimental merge 2026-10-06: independent Sol source and evidence
reviews approved `fe8a8e50` and `32c0c8a6`; exact-source T149 passed all eight
arms, retained in report-only `dbc54e2b`. Integration preserves that CPU source
unchanged. Six Tachi cells are qualified: scheduling-only grain16 is near
parity; compact grain17 is slower. Roci timing remains unmeasured because the
host was not quiet. Defaults unchanged; ticket stays open for residual host validation.

Authorized by the author on 2026-10-06. The reviewed T180 endpoint puts eight
independent conformer pairs in AVX2 lanes and iterates starts sequentially.
Pairs can cross molecule boundaries, but heterogeneous feature counts waste
lanes. Four starts of one pair have identical source records/counts and can
share coordinate broadcasts while retaining independent trajectories. T181's
negative feature-cooperation result does not test independent start lanes.
Use merged `35033d7` as the kernel baseline; upstream T158/T180/T159 residual
host validation is not an implementation dependency. Luna-max executes;
independent Sol-medium review is mandatory. Defaults remain unchanged.

## Scope

1. Specialize standard `start_mode=1` to eight independent trajectories:
   `[pair A starts 0,1,2,3 | pair B starts 0,1,2,3]`. Each lane owns quaternion,
   translation, gradient and Adagrad cache. Exactly four starts/25 steps in
   comparisons; do not confuse independent starts with cooperating feature
   lanes. Preserve existing paths for other start modes and unsupported inputs.
2. First implement a scheduling-only arm using the existing analytic evaluator,
   then a distinct compact-source broadcast/transform arm. Keep only two
   unduplicated source records. Each coordinate component can use two XMM
   `vbroadcastss` loads and `vinsertf128`, or a measured equivalent, to form
   `[A,A,A,A,B,B,B,B]`. Shared query coordinates may broadcast across eight lanes.
   Vectorize pose transforms where practical without folding in new arithmetic
   policies. Do not require a particular instruction sequence if another is
   demonstrably better. Inspect disassembly and report source traffic/packing.
3. Preserve polynomial/FMA/cutoff/guards and exact scalar fallback. Declare any
   transform/reduction change under D029; do not change exp grade, resolution,
   global compiler flags or optimizer settings. Preserve signed-permutation
   start conventions and independently validate per-lane effective poses.
4. Exact scalar final evaluation for every start, then deterministic best-start
   selection in original start order independently for each pair. Never reduce
   color gradients across starts. Preserve output order and ties, including
   conformers from different molecules and duplicate pair IDs.
5. Test counts 0..17, empty/uneven planes, asymmetric general matrices, different
   query pairs, poisoned padding, odd pair tails and 1/2/3/7/8/9-pair inputs;
   force unsupported numeric fallback and non-four-start dispatch. Compare
   fixed poses against the independent reference and ordinary optimizer ranks
   using existing T153/D029 gates; do not demand fp64 trajectory identity.
6. Analytic is primary. Add a bounded prepared-field companion reusing T159's
   query handles and target-type algebra, stored/interpolated gradients, and
   fast analytic unselected/out-of-grid fallback. Starts still diverge in field
   addresses: source broadcasting does not eliminate lookup gathers. Start
   with fp32 trilinear top1/top2 and fp32 brick top1; no representation sweep.
   Field/no-field trajectory differences are descriptive, not exact identity
   gates or retrieval-equivalence proof. Gate against the same-backend existing
   schedule, fixed-pose fixtures and exact scalar own-pose winner rescoring.
7. Preregister matched analytic baseline/scheduling-only/broadcast arms and
   field companions on ordinary groups 3/5/7 canonical/general, 128 library
   conformers, one physical core, four starts, 25 steps, mixing 0.5, three
   warmups/11 rotated repeats. Add a bounded short-pair diagnostic, not another
   large sweep. Record per-plane useful/issued lanes and setup/transform costs.
   Query field construction is outside all primary alignment calls; report
   build/packing/bytes and finite reuse separately. Instrumentation/native
   diagnostics are attribution only, never subtracted from full-call rates.

## Deciding measurement

Same-session whole-combo pairs/s and paired uncertainty against ordinary YMM8
pair lanes, separately for analytic and the same field backend/subset. Determine
whether identical-count start grouping improves ordinary throughput, not merely
short-batch occupancy. A bounded negative closes the experiment.

## Acceptance

- Independent fixed-pose, masks/tails/fallback and ranked-output checks pass;
  exact per-start/final scoring, tie order and four-start work are preserved.
- Scripts/protocol committed before runs; T118 decision-grade host lock,
  affinity/quiet checks, clean Release source/extension/ISA stamps, correct cwd
  and repeat metadata, matching populations, host-specific uncertainty.
- Roci and Tachi results stay separate; no default adoption, universal winner
  or multiplied speedup claim. Preserve unresolved host gates explicitly.
- Sol source/evidence review and fresh manual T149 on exact final source;
  integrated-source rerun if merging changes any scoring/codegen inputs. Keep
  `35033d7`'s reviewed noinline field-state boundaries intact.

## Traps

Pitfall 8: identical pair populations, not different count distributions.
Pitfall 16: stable best-start and canonical-ID tie order. Pitfall 18: analytic
coordinate loads already use SoA, so packing/transform benefits are not proof
of eliminating hardware gathers. Field addresses diverge after posing.
Pitfalls 22/23/27/28: shared corpora, committed scripts/results, visible ledger,
early pushes. Do not recreate T157 mining or reopen field accuracy.

## Working rules

Isolated worktree; never edit main or sibling worktrees/shared venv.
Read conventions, D029/D030/D031 and numeric/metrics policy before implementation.
T183 owns immediate Roci timing: hold ALL Roci CPU builds/tests during its
measurement windows. Prefer Tachi for bounded development if quiet; agree on
host reservations explicitly, use low build parallelism (2) and thread caps.
Use private verified extensions, durable per-ticket scratch and read-only
corpora. Commit/push early; no destructive sync or default promotion. Report
clean source candidates to the orchestrator for independent review before measurements.
