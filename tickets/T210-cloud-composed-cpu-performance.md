---
id: T210
title: Measure composed CPU search and attribute sustained scaling on the dedicated cloud host
phase: 2
lane: research
status: closed
model: luna
reviewer: sol
depends_on: [T209]
priority: highest
branch: ticket/T210-cloud-composed-performance
artifacts: results/T210/
---

## Sprint closeout — 2026-10-10

Closed for independently reviewed Phase A, larger-panel Phase B, existing-
evidence analysis and the author-authorized practical profiler/perf continuation.
See results (`results/T210/README.md`),
Phase B review (`results/T210/phase_b_review_20261009.md`) and
practical diagnostics review (`results/T210/simple_diagnostics_20261009/review.md`).
The earlier "attribution outstanding" sentence was overtaken by the completed
practical diagnostic tranche; no further precise-PMU framework is required.
All original exploratory/T118-refusal labels and setup-inclusive counter
boundaries remain unchanged. T211/T218 own later public/current-default rates;
optional detailed telemetry/cold-I/O/current-default weak scaling is T221.
Prepared-self public integration is reviewed; corpus precision is still T208.

This disposition supersedes earlier status/default statements below. Historical
scope, raw results, reviews and unmet criteria are retained for provenance;
closure is not a claim that every original experiment was performed.

## Historical context

The author authorized dispatch after T209 completed the Intel C4 setup. Assign
6-Luna-max as the sole cloud x86 VM benchmark execution owner; local T207 and
T167 agents develop independently. Consume reviewed merged code, not pending
branches. T204/T205/T206/T207 partial implementations are usable inputs; their
unclosed acceptance and T208 precision recomputation are not prerequisites
to accepted algorithm-design measurements and are not closed by this ticket.

## Scope

1. First commit a bounded protocol and runner changes for orchestrator approval.
   Reuse T207 composed/end-to-end harnesses rather than build a new framework.
   Freeze code/build/corpus/query/IDs/population/K, score semantics and complete
   CPU budget. Baseline field shape plus start-per-lane analytic color16,
   shared FP32 pose, prepared self overlaps, persistent worker-owned decoding
   and local reduction; T188/T192 switches remain OFF/OFF. Prove actual scan
   self evaluations zero. Explicitly qualify legacy shape volumes and exact
   once-prepared matrix-specific color; never claim precision certification.
2. Composed conformer and distinct-molecule top-K at a few useful K values
   (initial proposal 10/100/1000), with same-representation dense/reference
   score/ID/rank parity and complete unique-row/block census before timing.
   Separate query field build, once-only library preparation, repeated scan,
   final merge and full-call/finite-first-use accounting. Query field build
   must not determine large-library alignment comparisons.
3. Next bounded sustained physical/SMT scaling: propose 1/2/8/16/24 physical
   workers, SMT comparisons only at 8/16/24. Keep initial low-core repeats
   short and correctly labelled exploratory if T118 refuses their count;
   do not silently schedule 11 full-corpus repeats at one core. Enough unique
   work/scheduling units to avoid a 96-block/48-worker starvation test; audit
   available panel cardinality before choosing sizes, no repeated molecules
   relabelled unique. Distinguish strong from true weak scaling and measured
   imbalance from equal-row assumptions. The orchestrator approves bounded schedule first.
4. Then separate PMU/phase diagnostic sessions: cycles/instructions/refcycles,
   branch and L2 events, actual worker occupancy/work distributions and
   existing exclusive or explicitly nested phase timers. Standard PMU is not
   complete L3/DRAM/uncore bandwidth measurement. Probe counter usability and
   multiplexing and report limitations. No profile run concurrent with rates,
   no instrumented duration treated as production throughput or subtracted
   from it. Rank concrete next bottlenecks; causal follow-ups require a new
   orchestrator-approved scope, not automatic kernel edits.
5. Warm-cache first. Reuse/multiquery and independently verified I/O-inclusive
   behavior follow only if justified. Never drop global caches, mutate corpus,
   change sysctl/PMU provider configuration or deploy unreviewed candidates.

## Deciding measurement

Reproducible composed conformer/molecule throughput, K sensitivity, sustained
physical/SMT scaling and evidence-ranked residual bottlenecks. Evidence may
show no useful optimization target; report it. Stop after the approved bounded
matrix and analysis; do not expand to field/grain/precision tournaments.

## Acceptance

Orchestrator protocol approval before rates, then independent Sol-medium evidence
review. Clean frozen source, exact native/toolchain/build/corpus stamps,
canonical T118 lock/placement/load/provenance and raw grading limitations.
Fresh applicable T149 for codegen/scoring changes; native-input identity may
reuse T209's exact fresh canary with documented lineage for harness-only work.
Keep scripts/raw records/analysis under T210 and link T187/T190 residuals.
Report useful first results promptly; no cross-host ratio, default promotion
or scientific accuracy claim. Correctness failures block the affected arm.

## Traps

Conformer-K is not molecule-K; estimated memory is not observed RSS; equal
pair counts are not equal work. Separate first-use/prep from amortized scan.
Cloud isolation and counter availability do not waive noisy-run qualifications.
Do not multiply wins from separate experiments or hide sampler CPU overhead.

## Working rules

Private local clone/branch and private cloud source/builds; shared cloud corpus
read-only, do not mutate the T209 environment/install or source checkout.
Use the VM's shared `datasets/`, `runs/` and `locks/` areas and existing
environment read-only, on the exact registered cloud x86 VM host.
Only this agent launches cloud work; the orchestrator coordinates new reservations.
Max two compiler jobs; no build during timing. Commit scripts before runs,
sync results back locally, never push to GitHub.
Read conventions/numerics/T118 plus T207 protocols completely. Notify the orchestrator
at protocol readiness, first results, review readiness, blockers and completion.

## Execution status — 2026-10-09

Practical attribution is complete and independently reviewed under
`results/T210/simple_diagnostics_20261009/`: one 24P sampled profile and plain
aggregate perf-stat passes at 24P/48SMT, each with exact frozen Top-K parity.
The author replaced the planned precise-PMU framework with
these bounded whole-process diagnostics. All six counters report 100% running;
setup/preparation/finalization remain included. Analytic color batch8 accounts
for 64.84% exclusive samples, versus 6.15% for the principal field-gradient
routine. This prioritizes analytic-color follow-up, not a causal bandwidth
claim. Only the minimal launcher and actual evidence are merged.

The public prepared-self divergence is also fixed and reviewed; see
`results/T210/public_prepared_self/review_20261009.md`. Full T167 API/default
acceptance remains separate. No new throughput/default/precision claim follows
from the practical profiling tranche.

Phase A is complete on exact reviewed source `33b174df0c538cda8c11043fbab72bf648336d51` at W8, W24, and the single W2 conformer/K100 anchor. All prescribed correctness cells passed; exploratory rates and full walls, T118 refusals, point receipts, and the earlier no-rate failures are archived under `results/T210/`. Independent Sol-medium evidence review passed, as did the reviewed test-only historical-source fix and 225-test composition check with main. See the results summary (`results/T210/README.md`) and review receipt (`results/T210/phase_a_review_20261009.md`). Keep this ticket `claimed`, not closed: sustained larger-panel/SMT work and attribution are outstanding.

Phase B is also complete under its separately reviewed protocol and runner source `11021e6f9990bd169bff742580d9d169161149ce`: the transferred LIT-PCBA panel contains 3,605,026 distinct conformers and 882 physical blocks. Both ranking levels passed all scheduled correctness and balanced worker-only 24-physical/48-SMT comparisons. Independent evidence review passed, with approximately 8.3% conformer and 7.0% molecule scan-rate benefit from SMT on this finite panel. See the Phase B results (`results/T210/phase_b_runner/t210-phaseb-r3-20261009-01/README.md`) and review receipt (`results/T210/phase_b_review_20261009.md`). T118 remains refused under the explicitly short exploratory repeat budget; do not infer saturation or production defaults.

All 130 transferred files were verified against source sizes and SHA256 hashes. A separately reviewed, read-only existing-evidence analysis (`results/T210/phase_c_existing_evidence/README.md`) reproduces the recorded worker work sums and balanced allocation; it prioritizes the scoring-call envelope without asserting exclusive wall fractions or bandwidth causality. The remaining T210 work is separately reviewed PMU/phase attribution and an evidence-based assessment of useful follow-ups. No additional profiling/timing is authorized by the completed Phase A/B protocols.
