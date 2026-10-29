---
id: T218
title: Compose winning CPU color kernels and qualify the public screening policy
phase: 2
lane: kernel
status: closed
model: sol
reviewer: sol
depends_on: [T213, T214, T215, T216, T217, T219]
priority: high
artifacts: results/T218/
---

## Context

Final public three-mode qualification also requires T219: inspection on
2026-10-10 confirmed that T212 exposed combo workers only. Shape/rescore
ModeScan rates are not public api.screen rates; the synchronous public modes
must gain retained worker/context reuse before publishing that comparison.

T214–T217 deliberately isolate canonical specialization, force/torque factoring,
optimizer exponential and static fields. Their speedups do not multiply.
Integrate reviewed winners, resolve shared hot-loop patch overlap, and choose
one small public policy using composed rates and bounded exact-final top-K
validation. Negative sibling outcomes count as closed hypotheses, not blockers
requiring another candidate. Recommended 6.1-Sol-medium (Opus), independent
6-Sol-medium review.

## Scope

1. Compose only independently reviewed useful candidates on current main,
   keeping canonical detection and policy outside iterations. Preserve existing
   unoptimized general fallback, shared FP32 pose, worker-owned dataflow,
   prepared self and exact finals. Resolve interface/precision/order conflicts
   explicitly; do not blindly cherry-pick overlapping evaluator bodies.
2. Measure baseline, winning single analytic candidate, combined analytic,
   and selective-field combined candidate where its count class warrants it.
   One bounded ablation per uncertain interaction; no all-combinations sweep.
   Use the faster composed analytic cost to refresh T217's plane cutoff.
3. Run the public T212 route and reusable Engine, not only a special kernel
   benchmark. Report cold setup separately from warm scan; prove query fields
   do not rebuild on repeated public calls. Library-self Source-bound caveat
   remains unless separately authorized work changes it.
4. Confirm 24P and one targeted SMT or 8P check. Recompute shape/rescore/combo
   rates on the same final binary if a new ratio is quoted. Retire unsuccessful
   candidate variants or retain minimal experimental controls, avoiding a
   widened production dispatcher/code-size cliff.

## Deciding measurement

Composed public combo throughput, bounded conformer/molecule ranking gate,
static policy regret on sparse/dense classes and cold/finite/warm cost split.
Document remaining hotspot and real composed improvement versus main baseline.

## Acceptance

Small held-out ranking panel, exact final-score/fallback/worker regressions,
cache lifetime and memory tests, fresh exact-candidate T149, independent source
and evidence review. Defaults may move only for validated classes; analytic
fallback remains for unsupported or losing classes. This does not silently
close T162's full historical evaluation or T208 precision/corpus work.

## Traps

D012/D030: independently measured gains are not compositional evidence.
Do not pool different native binaries, populations or clock regimes into a
speedup. Do not let a mandatory dependency mean every sibling must be positive.

## Working rules

Follow CONVENTIONS.md and CPU-COLOR-CLOUD-EXECUTION.md. Own final composition,
public policy wiring and results only after sibling reviews; isolated branch,
exclusive cloud slot, local work on roci. No new kernel research or giant corpus.

## Staged integration (2026-10-10)

Initial analytic integration can start from reviewed T215 and T216 while
T214's timing and T217's field implementation proceed independently. This
does not waive the dependencies for final policy qualification: do not merge
an unreviewed sibling or promote an unmeasured default. T215 is already on
main as an opt-in; T216's raw-bit candidate has independently reviewed bounded
ranking and paired canonical full-scan evidence (7.04% gain).

The first stage replaces T216's private process-global selector with immutable
per-run/context selection and provides explicit approximate-arm T149 coverage.
Prepare the exp callable seam for T214, but only incorporate that candidate
after its fixed source and timing have passed review. Keep exact finals and
general fallback unchanged. Field-policy composition and cutoff refresh remain
later stages after T217 review; existing defaults stay unchanged meanwhile.

### Reviewed staged analytic merge (2026-10-10)

The call-local raw-bit exponential and torque-factoring composition is merged
as a public opt-in. Tested source `f8b21521`, report-only head `56681334`, and
independent review `8018bd83` approve this limited stage: 154 focused tests
passed (one intentional skip), the frozen eight-query composition panel passed,
and all 11 plain/canary arms matched in the fresh T149 report. The approximate
arms differ from baseline, confirming they were exercised. Exact finals and
general fallback remain unchanged; no process-global selector is used.

Defaults remain baseline. T218 stays open for composed public throughput,
T214/T217 integration where useful, cutoff refresh, and final policy
qualification. Individual T215/T216 gains are not a composed speedup claim.

### Reviewed public composition measurement (2026-10-10)

Measured source `bc63e21a` (production CPU source identical to staged main
`d3b54b05`), evidence-only head `9aa30732`, independent review `3c506280`:
matched public canonical screening of 3,605,026 conformers gave warm medians
14.8548s baseline / 13.3864s raw-plus-factoring at 24P (+10.97% throughput),
and 13.8873s / 12.3268s at 48T (+12.66%). Single 24P options gave +4.09%
factoring and +5.50% raw. This is actual composition, not multiplied gains.
Scan and public boundaries are reported separately, query handles are reused,
self bindings match, and full conformer Top100 membership overlap is 1.0.

One cold warmup and two timed repeats per arm are exploratory/T118-refused.
All timed process snapshots were clear; a cold 24P background snapshot is
retained but excluded from warm medians. Facade-created Source preparation is
inside each public call; cold public-minus-scan is not an isolated setup timer.
No independent full molecule Top100, default promotion or final field policy
qualification is claimed. T214 canonical helper composition and T217 field
cutoff refresh remain open.

### Reviewed canonical composition merge (2026-10-10)

Source `e3256ba9`, report-only head `61ae0e1`, independent source review
`b1dea24d` and runner-fix review `32311c41` approve the default-OFF
`canonical_color_kernel` public per-run control. The dedicated T214 helper
shares compile-time baseline/raw callables and torque factoring; linked
assembly confirms inline raw weights without exp calls, indirect calls or
per-Gaussian polishing/mode branches. Existing invariant-plan control remains
independent, and T217/general/field/exact-final behavior is preserved.

Local 177 tests passed (one intentional skip), the frozen ranking panel
passed, and the fresh 11-arm canary matched at clean source. The SMT
prerequisite now binds comparison mode and exact arms as well as provenance.
Cloud canonical OFF/ON comparison is complete and independently reviewed:
measured source `61ae0e1`, evidence `466deb59` plus preservation receipt
`acdee6bb`, review `7a291ce6`. Matched prior raw-plus-factoring OFF versus
canonical ON public medians were 13.3556s / 12.2086s at 24P (+9.39%
throughput), and 12.3458s / 11.1461s at 48T (+10.76%). All saved score/GID/MID
arrays match across arms, repeats and points; all process snapshots were clear.
These are incremental same-session gains, not multiplied historical gains.
One cold warmup/two repeats remain exploratory/T118-refused. Defaults remain
unchanged, and field cutoff/final policy qualification remains open.

### Reviewed matched public mode comparison (2026-10-10)

T219 explicit public workers are merged. Final measured runner source
`4963f7ab` contains reviewed benchmark-only patch equivalents; native source
is unchanged from reviewed T219 `b12d8890` (CPU SHA256 `ef508181...`, DSO
`0c7407ed...`). Artifact-only evidence `86b9f097`, independent review
`dee95d6d`, retained under `results/T218/public_modes_cloud_20261010`:

| Explicit public worker mode | 24P conformers/s | 48T conformers/s |
|---|---:|---:|
| Shape-only | 972,012 | 1,063,958 |
| Shape search + exact color rescore | 860,709 | 939,753 |
| Full combo, canonical + factoring + rawbits | 298,691 | 324,988 |

Each point has one cold warmup and two timed full 3,605,026-conformer scans per
mode, query fields reused. Public wall includes facade-created Source library
preparation; scan boundaries and cold setup are separately preserved. All 18
saved final arrays/hash bindings match within each mode across repeats and
points. Native affinity is full singleton 24/48; foreign-process snapshots
are empty. Short-repeat results remain exploratory/T118-refused, not default
promotion, cross-objective ranking equivalence or independent molecule Top100.
The old general-matrix roughly-sixfold ratio is not a direct speedup comparator.

Remaining policy work: a bounded exact-algebra AUTO-combo tranche is assigned
to 6-Luna-max (Haiku), with 6-Sol-medium review. Only auto-generated public
combo options enable canonical specialization/factoring; rawbits remains
explicitly approximate/opt-in, explicit options and ordinary shape/rescore
defaults stay authoritative. Correct the stale noncombo VAA-conversion stats
label (source/README currently have the correct arithmetic). T213/T215 also
receive a short current-fast-combo perf attribution pass, not another kernel
or benchmark-framework exploration. Default qualification remains open.

### Reviewed fast public defaults (2026-10-10; outcome)

The author authorized promoting the validated composed analytic implementation,
including approximate optimizer exp, rather than retaining the exact-only
intermediate policy above. Frozen source `c19df18c`, strict T149-only commit
`9e477f2b`, and independent final review `98579ea1` approve this policy:

- `CPUWorkerOptions` leaves the three optimizer-color controls automatic by
  default. The public worker boundary resolves combo to canonical helper and
  torque factoring enabled with `optimizer_exp_mode="rawbits"`. Both implicit
  `api.screen` combo and explicit worker options use this policy.
- `optimizer_exp_mode="baseline"` opts out of approximate exp while retaining
  unspecified exact-algebra optimizations. Explicit `False` disables either
  exact optimization. Unsupported/noncanonical interactions retain the native
  general baseline path; exact per-start/winner scoring is unchanged.
- Shape/rescore resolve automatic controls to disabled/baseline. Low-level
  reference/worker defaults, memory budgets, and ordinary implicit shape/rescore
  routing are unchanged. No field construction is added to the default path.

Current focused tests: 169 passed, one existing uncompiled experimental-grain
skip, expected CPU-only arithmetic warning. Real-public regression coverage
checks resolved defaults, opt-out, nonzero cross-plane general fallback against
explicit baseline, and shape/rescore compatibility. The previously reviewed
eight-query raw-plus-factor-plus-canonical panel passes the agreed finite/top-K
gates; this Python-only policy change does not alter those native kernels.
Fresh T149 passed all 13 arms with no moves and clean matching native stamps.
The report-only gate and separate focused evidence are preserved under
`results/T149/premerge/T218-fast-combo-defaults-c19df18.json` and
`results/T218/fast_combo_defaults_verification_20261010.md`.

Close this bounded composition/public-policy ticket. The matched public rates
above remain exploratory and are not a twofold same-workload kernel speedup.
T217's tested fields lost excluding construction, so the default stays analytic;
further field cutovers remain separate research, not a prerequisite for shipping
the measured winner. The short perf diagnostic is reviewed/archived but cannot
provide current color-only attribution. This closure does not close T162/T208,
certify corpus precision/global-optimum recall, or change the memory policy.
