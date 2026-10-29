# Conventions

## Amendment 2026-10-14: portable tests and flat internal evidence

The internal repository retains individual structured results files and readable
reports under `results/TNN/`. Do not consolidate ticket directories into solid
archives. Individually compressed oversized files remain appropriate; keep
existing original payload/provenance hashes and document their encoding.

Correctness tests must not depend on historical commits, historical Git diffs,
private developer worktree paths, or old campaign approval receipts. Exercise
validators with synthetic records or temporary repositories; generic Git/build
stamp behavior tests remain valid. Historical commit IDs in scientific evidence
are provenance, not instructions to rewrite that evidence after filtering.

Whole-history CPU ledger certification is an explicit developer audit through
`scripts/audit_cpu_result_ledgers.py`, not a product correctness prerequisite.
Frozen ticket-protocol/approval audits live in `bench/audits/` and run only when
explicitly requested, not as part of default pytest collection.
Synthetic missing-ledger checker tests remain in the normal suite. Never invent
old run records to make an audit pass. Minimal numerical/static fixtures should
be independent of old Git history; new fixtures belong in `tests/data/` or
`tests/artifacts/`, rather than depending on a developer's experiment checkout.
Keep experiment summaries structured when useful, without adding a new archive
or summarization framework as a requirement.

Every rule here applies to all work in this repository. Ticket files reference
this document rather than reproducing it -- in our earlier ROSHAMBO2-fork project roughly
36 lines of the text below was copy-pasted into 22 ticket files, which is how it drifted.

The numbered pitfalls in particular are cross-referenced **by number** from
tickets' Traps sections.


## GPU lock protocol

Two environment variables stand in for anything machine-specific, so nothing here names a host:
`$ROSHAMBO3_CORPORA` is where corpora live and `$ROSHAMBO3_GPU_LOCK` is the base path of the arbitration lock files.
Both are read in exactly one place, `roshambo3/paths.py`, which also carries the defaults. In this
public copy, host-specific paths in the historical archive are replaced by placeholders.

This machine has one GPU, and concurrent lanes contend for it. Every ticket's Working rules section reproduces this in
full, but the summary: before any benchmark, check `nvidia-smi --query-compute-apps=...` and
`nvidia-smi --query-gpu=...` and abort if another process holds the card. Any run whose number
will be *quoted* (cited in a decision, a comparison, or a closed ticket's deciding measurement)
must hold the per-device GPU lock for the run's duration, with the ticket id
and PID written into the lock file: `bench.gpu_lock.GpuLock` (or the shell recipe in
`CLAUDE.md`). `$ROSHAMBO3_GPU_LOCK` is the base of a per-host, per-device family of lock
files (`roshambo3/paths.py::gpu_lock_path`), so `flock $ROSHAMBO3_GPU_LOCK` itself excludes
nothing. Correctness-only work (unit tests, tiny kernels not being
timed) may run unlocked. A run that finds the GPU busy and proceeds anyway is `advisory`, not
`decision` -- it can inform intuition but must never be the number a ticket closes on.

## Clock control and operating points (D007)

**Profilers seize the GPU clock.** `ncu --clock-control` defaults to `base` and overrides
`nvidia-smi -lgc` for the duration of a profiling run. A clock observed *above* the locked value,
or rock-steady at a value nobody configured, is the profiler -- not a failed lock. Check
`ps aux | grep -E "[n]cu|[n]sys"` first.

**Never combine numbers taken at different clocks** into one ratio, table, or derived quantity.
Counters from `ncu` runs are comparable among themselves; timings from locked-clock runs are
comparable among themselves; across the two they are not.

Every run records the *achieved* clock distribution, the `sw_power_cap`-active fraction, whether
a profiler held clock control, and which clock any percent-of-peak was normalised against. A
power-capped run was power-limited, not clock-locked. See `decisions/D007` and `tickets/T26-harness-clock-enforcement.md`.

## Bottleneck attribution (D009)

**Never claim a bottleneck from warp stall-reason shares.** `not_selected` means a warp was
*eligible and lost scheduler arbitration* -- it is not a stall, and it is evidence against latency
starvation rather than proof of throughput saturation. Claim from `smsp__issue_active`,
`sm__inst_issued`, and the dominant pipe. **Causal ablation outranks every counter argument**;
where both exist, say whether they agree.

**A high L2 hit rate does not make excess sectors free** -- they still cost L1TEX wavefront
capacity, XBAR/L2 bandwidth and return bandwidth.

See `decisions/D009` for the measured state and the case that produced the rule.

## Waiting on long jobs (D011)

**Wait on the progress signal, not the terminal artefact** — if the job streams a log line per
work unit, poll that; partial results are results. **Never issue a blind `sleep N`** (it cannot
detect early completion or failure); bound every wait by a condition with an iteration cap.
**One waiter at a time.** **Prefer doing analysis to waiting.** Jobs under ~10 minutes belong in
a single foreground `Bash` call with a generous `timeout`. **Commit before you wait** — three
agents have been killed mid-run by API errors and two lost everything.

Four agents have already lost large budget fractions to this; see `decisions/D011`.

## Concurrent agents: your siblings are not intruders

> The worktree layout and branch convention in this section are ROSHAMBO2's; see "Corrections
> carried into ROSHAMBO3" at the end of this file.

Several tickets run **at the same time**, each in its own git worktree under
`<worktree-root>/T<NN>/`, on its own `ticket/T<NN>-<slug>` branch. You will therefore see
worktrees, branches, and in-progress uncommitted work that you did not create and were not told
about. **This is expected and legitimate. Do not clean it up, revert it, delete it, or treat it
as evidence of a rogue process.**

Rules:

- Touch only your own worktree. Never `git worktree remove`, never delete a branch, never commit
  to another ticket's branch, and never commit to the integration branch unless your ticket says to.
  (In ROSHAMBO3 the trunk is `main`, and it is never committed to directly at all -- work lands
  by pull request. See the corrections at the end.)
- If you believe another agent has done something wrong, **report it and stop** -- do not act on
  it. You cannot see the orchestrator's dispatch history, so you are not in a position to judge
  whether work outside your worktree was authorized.
- Uncommitted changes in a sibling worktree mean that agent is mid-flight. Deleting them destroys
  live work.

This section exists because it already happened once: the agent that generated these ticket files
observed the concurrently-running T01/T02/T05 agents, correctly noticed it had not been told about
them, and reasonably concluded something had gone wrong. Nothing had. It preserved everything and
asked before acting, which was the right call -- but the confusion was avoidable, and this note is
the fix.

## Numbered pitfalls

Every ticket's Traps section cross-references these by number (from the plan's "Pitfalls -- read
before running anything" section, ranked by probability × damage):

1. The loaded `.so` is sm_75 and JITs on Blackwell -- `rm -rf build` and verify with
   `cuobjdump --list-elf` before timing anything.
2. Benchmarking while someone else uses the GPU -- check compute-apps and hold the lock; a run
   that finds the GPU busy is advisory, not decision.
3. Accuracy on synthetic random molecules -- `make_large.py` gives every Tanimoto in
   [0.9975, 1.0000] spanning ~4,000 float32 ULPs, with V_BB 56x too large and `n_real = L` for
   every molecule, hiding the two effects worth 7.8x.
4. An unconverged reference -- `start_mode=0` is off by +0.107 on the true top-50. A candidate
   exceeding gold on >0.1% of pairs by >1e-3 is evidence gold is unconverged, not that the
   candidate is better.
5. "C++ and CUDA agree, so the math is right" -- they agree because they share the typo. Keep the
   permanent `‖q‖` and Cauchy-Schwarz assertions.
6. The `min(V_AA, V_BB)` volume bound -- false for this scoring function (ratio up to 2.25; a
   T=0.934 hit inside a band the bound calls ≤0.80). Use Cauchy-Schwarz; expect 1.19-1.50x, not
   5.6-11.3x.
7. Unoptimized builds -- the manual `cmake ..` path leaves host code at `-O0` while device code
   stays `-O3`.
8. Padded-batch size outliers -- two configurations compared for throughput must have identical L
   histograms, or the comparison is between data layouts, not kernels.
9. Conflating conformer-level and molecule-level recall -- report both, always; stratify
   molecule-level recall by conformer count.
10. Tuning and evaluating on the same data -- +0.0092 inflation at K=30.
11. Measuring only kernel time -- host reduction is 3.5x the kernel; decode+prep is 12x slower.
12. `max_results` silently truncating what you are measuring -- default 10,000 < 100,000, applied
    per batch before merging.
13. Cherry-picked queries -- the 1e-4-quantile threshold ranged 0.70-0.95 over four random
    queries.
14. Small-batch GPU benchmarks -- N=1e4 under-reports by 5x. Minimum 1e6 conformers per launch.
15. Premature energy optimization -- 13.4 W of 300 W at 180 MHz of 3090 max, idle. Log power from
    day one; do not treat joules as the currency until a sustained run is measured within ~15% of
    the limit.
16. Float32 ties and unstable sorts -- canonical id tie-break, identically for gold and candidate.
17. Page cache making I/O disappear -- for any I/O-inclusive number, drop caches or use a dataset
    ≥3x RAM (≥375 GB, i.e. D5).
18. Extrapolating a shape-only speedup to the color path -- color loops run over the entire
    padding region, so cost grows as (L - n_real)^2.
19. Compound ids with a conformer suffix -- `rsplit('_',1)` silently merges distinct molecules.
20. Descriptor row-order joins -- a descriptor file can have fewer rows than the corpus. Join on
    the parquet `molecule_id`, never row order.
21. Train/evaluation leakage -- verify no overlap between tuning data and evaluation sets, and
    record the check.
22. Copying datasets into a worktree, or putting them on the home volume -- bulk data lives once at
    `$ROSHAMBO3_CORPORA`, shared by absolute path or read-only symlink.
23. Leaving an eval script in a scratchpad -- if it produced a number, it belongs on project
    disk, committed on the ticket branch.
24. Treating this plan's performance numbers as measured -- only items tagged *(measured)* are.
25. Running `tickets/T78/r3_build.py` without `--log <your own path>` -- the default
    **appends** to `results/T78/build_sm120-g0-t256.log`, which is committed T78 evidence, so a
    routine rebuild silently grows a closed ticket's ptxas record by thousands of lines. Hit
    2026-08-26 rebuilding main after the T86 merge; caught by `git status` and restored.
26. Passing `-q` to pytest -- `pyproject.toml` already carries `-q` in `addopts`, so your `-q`
    makes it `-qq` and pytest **prints no summary line at all**. The run still exits 0, so a
    truncated capture looks like a pass with no tally. Run plain `python -m pytest --no-header`,
    or count the progress characters.
27. Leaving a claimed ticket's file only on its own branch -- the ledger is read from `main`, so
    a ticket that exists only on `ticket/TNN-...` is invisible to anyone looking at the repo, and
    "is this work recorded anywhere?" becomes a question the conversation has to answer. **Commit
    the ticket file to `main` when the ticket is claimed**, not when it merges; the branch carries
    the scripts and results. Observed 2026-08-27: T95 was claimed, running, and pushed, and still
    could not be seen from `main`.
29. **`GROUPS` is a bash special array** holding the current user's group ids. `GROUPS=0,1,2,3,4,5`
    *appears* to assign -- it prints as assigned even under `set -x` -- and then `"$GROUPS"`
    expands to a gid such as `1000`. T101 hit this: its first sweep silently screened group
    1000 and reported "refused" on every arm, **which reads exactly like a real shared-memory
    refusal**. Never name a shell variable `GROUPS`; the same applies to `UID`, `PPID`,
    `RANDOM`, `SECONDS` and `LINENO`.
30. Comparing derived float metrics for exact equality across two builds. T101's first
    cross-level check compared BEDROC with `==` and reported a spurious FAIL on 12 of 16 cells
    at 4.5e-16 relative. Compare the **ranking** the metric induces (`numerics.rank_order`),
    which is what D013 accepts on, not the metric's last bit.
28. An agent branch that exists only on the local disk. `git push roci <branch>` early and often:
    a worktree is not a backup, and D011's "commit before you wait" is only half the rule.

31. Reading a GPU allocation you cannot attribute as a leaked context. A process listed by
    `nvidia-smi --query-compute-apps` that does not resolve locally is not necessarily a dead
    process holding a leaked CUDA context, and **it is not ours to reap.**
    Before treating GPU memory as leaked, check whether the card is actually *doing*
    anything (`utilization.gpu`, `clocks.sm`). A quiescent allocation costs memory, not
    throughput; a busy card disqualifies a timed run, and where clocks cannot be locked (D004)
    concurrent load also perturbs results. Check utilization, not just occupancy.

32. **A stop rule that no script evaluates.** A ticket that specifies when to stop -- a
    convergence threshold, a marginal-gain floor, a "close negative if the crossover lands
    above the panel" -- has specified a *measurement*, and a measurement nobody computes
    does not exist. **Write the rule as code that runs each stage and writes its value into
    the run record**, next to the number the rule is about.
    Measured instance, T145: the ticket said *"stop when a decade of effort moves fewer
    than 0.1% of pairs by more than 1e-3."* Nothing computed it. Stage C was launched at
    **129x its specified size** (51,600 passes planned against a specification of ~400)
    and had run **~64x** (25,650 passes) for **82 hours of
    two-GPU time** before a human checked. Re-derived afterwards on cumulative spans
    (`tickets/T145/decade_convergence.py`, `results/T145/decade_convergence.json`), the
    reference had entered the stop region **during stage B**, at cumulative pass ~3,744 of
    an eventual 37,794: everything after that point -- **34,050 passes, 90% of the run,
    including all of stage C** -- moved 0.0096% of pairs by more than 1e-3, ten times
    inside the threshold.
    **Do not read that as "the missing code would have saved 90%", which an earlier draft
    of this entry implied and the second review corrected.** That figure is measured
    backwards from the end. A rule you can actually stop a run with is evaluated on the
    *trailing* decade as the run proceeds, and that monitor reads 0.81-1.64% at the end of
    stage A and 1.21-1.42% at the end of stage B -- outside, both times -- and is provably
    unable to fire before cumulative pass 34,080, because every earlier window contains
    [3,408 -> 12,144] at 0.1793%. It would have stopped the run at ~34,080 of the 37,794
    that ran: **about 10%, or 47% against the 63,744 specified.** The GPU-days went to the
    *sizing* overruns -- stage B at 1.81x its specification, stage C launched at **129x** (~64x executed) -- which
    are a different defect. **A stop rule does not protect you from a badly sized schedule,
    and an entry that implies otherwise teaches a remedy for the wrong failure.**
    **And the hand-check that finally ran it was itself wrong, which is the second half of
    this pitfall.** It compared stage C's own 3.11x increment against a threshold
    calibrated for a decade (10x), used a mid-run snapshot value (0.0064%) where the
    final-state figure is 0.0077%, and reported the result as "16x inside". That reading
    went into the artifact's manifest and stood for a day. **A rule computed by hand, once,
    at the end, is not the same object as a rule computed by code at every stage boundary**
    -- the hand version has no second chance to notice that it measured the wrong span.
    Three things make this hard to see, and they are why it earns a number:
    * **Nothing fails.** A run past its stop rule is not an error, produces no warning, and
      its logs look exactly like a run that is still working. Every other refusal in this
      project fires *against* something; this one has nothing to fire against.
    * **The mean hides it.** T145's `mean_score` moved ~1e-6 per day, which reads as
      converged -- while a heavy-tailed per-cell distribution was still moving four orders
      above that. **Judge a stop rule on the statistic the rule names**, not on whatever
      the job already logs. If the rule is about the tail, the log must carry the tail.
    * **A rule about a *span* is easy to evaluate on the wrong span.** "A decade of
      effort" is 10x *cumulative* effort; the increment a stage happens to be is whatever
      the schedule made it (T145's stage C was 3.11x). If the rule names a span, the code
      that computes it must compute the span too, from the run's own pass counts, and
      write the achieved ratio into the record next to the value -- otherwise the number
      looks like an answer to the rule and is an answer to a different, easier question.
    This is the same generator as pitfalls behind **T52** (refusals implemented but
    unreachable), **T128** (a fixture that skips rather than fails) and **T131** (rules
    implemented and never called): *a check that does not run cannot fire.* T145 is the
    first instance to cost GPU-days rather than a wrong number, which is exactly why it
    went unnoticed -- the others produced a suspicious artifact, and this one produced a
    progress bar.

## Model names -- two hierarchies, both live

`model:` and `reviewer:` name a **model tier**, and the reviewer is a different
family from the implementer on purpose: pitfall 5 applies to two agents of one
family reading the same repository and the same block comments.

**Two agent systems work this repository and name the tiers differently.** Both
naming schemes are correct and neither is rewritten, because the other system
reads these files too:

| in a ticket | dispatched here as |
|---|---|
| `astra` | `fable` |
| `sol` | `opus` |
| `terra` | `sonnet` |
| `luna` | `haiku` |

T153-T168 carry the first scheme; everything else carries the second. **Do not
"normalize" a ticket's frontmatter to one scheme** -- that breaks the other
system, and it was tried once (2026-09-12) and reverted.

`scripts/ticket_index.py` renders both, so `INDEX.md` shows `astra (fable)` and
the translation is read rather than remembered. That is deliberate: "look up the
mapping before dispatching" is a thing to remember, and T131 is what this
repository calls a rule that depends on someone remembering it.

## Working rules

Enforced in every dispatch, no exceptions:

1. **Independent git worktree per ticket.** `git branch ticket/T<NN>-<slug> main`, then
   `git worktree add <worktree-root>/T<NN> ticket/T<NN>-<slug>`. Never work directly in the
   main checkout.
2. **Share datasets, never copy them.** Corpora live once at `$ROSHAMBO3_CORPORA`
   (`roshambo3.paths.corpora_root()`) and are referenced by absolute path or symlinked read-only.
   Put them on the fast, large volume; source and small artifacts go on the home volume. A ticket
   that copies an internal corpus or D5 (86 GB) has already failed.
3. **Independent scratchpad per agent**, for throwaway work only — nothing that produces a
   reportable number may live only there.
4. **Every eval, benchmark and analysis script is written to project disk** under `bench/` or
   `tickets/T<NN>/`, committed on the ticket branch. Nothing that produces a number may live only
   in a conversation or a scratchpad — those are lost, and then the number is unreproducible.
5. **Results go to `results/T<NN>/`** as run-record JSONL plus artifacts, committed (or, for large
   artifacts, stored beside the corpora with the path and sha256 recorded in the committed run
   record).
6. **The orchestrator delegates and stays out of the details.** Whoever holds the overall thread
   reads ticket outcomes, not file dumps — report the conclusion plus the artifact path.

### Required manual CPU scoring/codegen pre-merge check (T149)

For any proposed change that can affect CPU scoring results or CPU score-kernel code generation,
the reviewer must require a fresh T149 canary run before approval/merge. This applies at least to
changes in `src/roshambo3/backend/_cpu_src/`, CPU scoring dispatch/optimizer logic, CPU compiler
flags or toolchain/build configuration, and dependencies that affect that compiled path. This is a
manual review gate, not CI.

Run from the root of the committed candidate worktree, with the shared Python environment that has
NumPy and pybind11 available. Before the build starts, `git status --porcelain --untracked-files=all`
must be empty; the runner enforces this check. The report file is created only after that check.

```bash
t149_run_id="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short=12 HEAD)"
python tickets/T149/inlining_canary_ci.py --output "results/T149/premerge/${t149_run_id}.json"
```

The two-build direct-CMake command must complete on the exact candidate source revision being
reviewed. Commit the JSON report under `results/T149/premerge/` and link it in the review. The
reviewer verifies and records the report's run date (UTC), candidate `source_commit`, runner
commit, compiler/CMake versions, eight plain/canary arm hashes, both loaded extension paths and
source/build stamps, `arms_that_moved`, and `passed`. The report records HEADs and porcelain status
before and after the builds/scoring; each before/after HEAD pair must be identical, both worktrees
must remain unchanged, and the runner must abort without writing a report if this check fails. For
the routine manual check, both runner/source worktrees must be clean before and after the run, with
empty porcelain fields. Both extension paths must be distinct isolated installs. The ON/OFF CPU
source hashes and trees must agree, and both stamps must report `cpu_src_dirty: 0` with no dirty
source files. After the report is committed, require another clean
`git status --porcelain --untracked-files=all` before review/approval and verify
`git diff --name-only <source_commit>..HEAD` contains **only** the exact report file
`results/T149/premerge/<run-id>.json` linked in the review. This explicitly permits the post-run
evidence-only commit; `source_commit` is the tested code revision, not the report commit or merge
HEAD. Any code, runner, fixture, build-configuration, dependency, or CPU scoring/source change after
`source_commit` requires a new run. Approval requires process exit 0, `passed: true`, and no changed
arms. Any build/import/provenance failure, missing report field/artifact, mismatch, dirty pre-run or
post-commit tree, or any other diff from `source_commit` fails closed: do not approve based on an
older green run or label the check advisory; correct the issue and rerun. The harness's
`--allow-dirty-source` escape is only for separately labeled restored-counter source-variant
experiments; it records the dirty status and must never be used for the routine manual check.

This routine green check does **not** discharge T149's separate historical acceptance test: the
exact restored T136 census counter must also produce the required red result. Keep that gate
explicitly unresolved unless a qualifying run demonstrates it.

## Corrections carried into ROSHAMBO3

The text above is reproduced from the ticket system of our earlier ROSHAMBO2-fork project. Two items were true when written
and are not true now. They are corrected here rather than silently edited above, so the change is
visible to anyone following a citation.

- **Pitfall 17 (page cache) names D5 as a dataset "≥3x RAM (≥375 GB)". D5 is 86 GB.** The 460 GB
  figure predates the `.rsb3` format, which shrank the corpus roughly 5x. This machine has 125 GB
  of RAM, so **D5 now fits in page cache** and is no longer a defence against it. For any
  I/O-inclusive number, drop caches explicitly and verify: use `posix_fadvise(DONTNEED)` plus
  `mincore`, and record `resident_fraction` in the run record. See `tickets/T47-producer-path-placement.md`.
- **Worktrees and branches.** ROSHAMBO2 used a fixed worktree root and cut ticket branches from
  a dedicated integration branch, because of a Git ref-name collision (a ref could not simultaneously
  be a leaf ref and a path component). That collision does not exist here: branches are cut from `main`, and a
  worktree goes anywhere outside the checkout. The `ticket/T<NN>-<slug>` naming is unchanged.

---

## Amendment 2026-08-21: the two-machine protocol, and what committing means

Added for a period that ran six lanes concurrently across two
machines. Everything here is an extension of the Working rules above, not a replacement.

### Where things live

- **Worktree root.** Use one fixed worktree root on each host (outside the checkout).
- **Durable scratch is `<scratch>/T<NN>/`** on the large data volume of roci or
  tachi. Not the home volume, and never inside a
  worktree — pitfall 22. A session scratchpad is for throwaway work only, per Working rule 3.
- **Corpora**: `<corpora>`, at a different location on roci and
  on tachi. Export `ROSHAMBO3_DATASETS`
  accordingly; several archived scripts hardcode roci's path as a module-level constant with
  no per-host branch.

### What "commit before you wait" means in practice

D011's rule is a floor, not a ceiling. Concretely:

- **Commit any script before you run it**, not after it produces something. Working rule 4
  says a script that produced a number belongs on project disk; the reason it must be
  committed *first* is that the run is when the process is most likely to die.
- **Commit at least every thirty minutes of work**, and always before a run expected to
  exceed ten minutes.
- **Flip the ticket's `status:` to `claimed` in a commit as your first act**, so a sibling
  can see the lane is taken without asking the orchestrator.
- A heredoc is not a script. Neither is a shell history entry. If it produced a number and it
  is not a committed file, the number is unreproducible and pitfall 23 has already happened.

### tachi

roci holds the git remote of record for both machines. Both machines push and fetch normally.

**The `git bundle` → `scp` → `git reset --hard` pattern in `tickets/T17/sync_tachi.sh` and
`tickets/T20/sync_tachi.sh` is retired.** Its failure mode is the one this whole section
exists to prevent: it hard-resets tachi's checkout, so results not `rsync`ed back *first*
were destroyed silently, and the ordering constraint lived only in a script comment.
`results/T<NN>/` now travels as commits.

D006's rule is unchanged and still binds: **results come back to this repo. tachi is compute,
not storage of record.**

Building there:

- **CUDA 12.9 is installed system-wide** (nvcc 12.9.86, driver
  580.173.02, verified 2026-08-21). **The earlier locally fetched toolkit recipe is retired** —
  `tickets/T03/fetch_cuda_toolkit.sh`, `build_toolkit_variant.sh`, and every tachi build
  script pointing at that toolkit are history, not instructions. Do not copy
  them forward.
- Build `-DCMAKE_CUDA_ARCHITECTURES=70-real`. roci's pinned CUDA 13.2 **cannot** target
  sm_70 at all; that is a hard toolkit floor, not a setting. Verify the embedded SASS with
  `cuobjdump --list-elf` — pitfall 1 is the highest-yield mistake in this project's history.
- Two TITAN V, 12 GB each. Select one with `CUDA_VISIBLE_DEVICES`; two lanes may hold the two
  cards concurrently, as T17 and T18 already did.
- **Until the per-device telemetry ticket lands, the shared harness's clock and contention
  numbers are GPU-0-only.** `bench/gpu_lock.py::query_gpu_state()` and
  `bench/clocks.py::ClockPowerSampler` both call `nvidia-smi --query-gpu=...` with no `-i`
  index, so on a two-GPU host they report device 0 whatever ran the kernel; and the
  compute-apps check spans all devices with no device column, so a stale allocation on the
  card you are *not* using reads as contention. Documented in
  `tickets/T30/probe_vs_production.py:62-70`, where it was hit.
- `ncu` counters and clock locking are not used there. Attribution is
  causal-ablation only (D009); report achieved clock distributions (D007, D023).
- tachi has 128 GB of RAM as of 2026-08-21. **Pitfall 17's correction now applies to both
  hosts**: D5 at 86 GB fits in page cache on either machine, so any I/O-inclusive number
  needs an explicit `posix_fadvise(DONTNEED)` and a `mincore` check.

### Which ROSHAMBO2 you are comparing against

See `decisions/D024`. Five states exist, three differ by factors large enough to change a
headline, and one of them is our own fork rather than ROSHAMBO2 at all. Name the commit in
the run record. The reference is our numerics-fixed fork `fix/numerics` (`33ef8e1`).

### Which clock regime you are in

See `decisions/D023`. Calibration runs lock the clock; headline runs unlock it. Both record
the achieved distribution, and a number from one regime may never be combined with a number
from the other.

### Testing from a worktree: the shared venv lies to you, in both directions

Discovered 2026-08-21, with eight lanes running concurrently. **Read this before
you trust a green test run from a worktree.**

The shared venv was `pip install -e .`'d
from the main checkout, and scikit-build-core's editable install registers a
`ScikitBuildRedirectingFinder` in `sys.meta_path` that maps every `roshambo3.*`
name to a **fixed absolute path under the main checkout's `src/`**.
`sys.meta_path` is consulted before `sys.path`, so:

```
cd <worktree> && <shared-venv>/bin/python -m pytest
```

**silently tests the main checkout's code.** Your edits are invisible. There is
no error and no warning, and nothing in the output says which tree ran — a false
pass or a false failure, either way.

Stripping the finder and prepending the worktree's `src/` trades that for a
second silent failure. The compiled extension is **not** in the source tree: it
is at `.venv/lib/python3.11/site-packages/roshambo3/_roshambo3_cuda*.so`, in a
directory that holds only the `.so` and no `__init__.py`. Once the worktree's
`src/` owns the `roshambo3` package name, the submodule lookup uses that
package's `__path__`, the extension is not found, `with_cuda` comes back
**False**, and **every GPU test skips** — a suite that goes green having tested
nothing.

Use **`bench/worktree_python.sh`**, which does both halves and prints the tree
and extension it resolved:

```
<main-checkout>/bench/worktree_python.sh -m pytest -q tests/
```

One shared copy serves every lane — it takes the worktree from the caller's
directory, so run it from inside yours. From the main checkout it passes
straight through.

**If your lane changes CUDA, that script refuses, and it is right to.** The
installed `.so` was built from the main checkout's device code, so Python from
your tree against that extension is a result belonging to neither. Build your
own venv in the worktree:

```
cd <worktree>
uv venv --python 3.11 --allow-existing
CMAKE_ARGS='-DROSHAMBO3_ARCH_NATIVE=ON' uv pip install -e .
```

**Never `pip install -e .` from a worktree into the shared venv.** It rewrites
the redirecting finder's baked-in path to point at your tree and breaks every
other concurrent lane — see "your siblings are not intruders" above.

Whatever route you take, **assert what you loaded**. A run that does not check
`roshambo3.__file__` and `get_build_info().with_cuda` can be wrong in either
direction and look fine.

**And export these, or ~60 tests skip silently.** With `ROSHAMBO3_CORPORA` unset,
the corpus-backed tests resolve against `paths.DEFAULT_CORPORA`
(`/var/lib/roshambo3/corpora`, deliberately generic) and skip;
`ROSHAMBO3_TEST_SDF` gates the whole prepare suite the same way. Measured
2026-08-21: unset, the suite reported ~60 skips and still said "passed"; set, one
skip remained and everything passed.

```
export ROSHAMBO3_CORPORA=<corpora>
export ROSHAMBO3_TEST_SDF=<test-sdf>
export ROSHAMBO3_GPU_LOCK=<lock-base>   # a BASE, not a path
```

**`ROSHAMBO3_GPU_LOCK` unset is worse than the other two, because it fails
silently in the direction of *no mutual exclusion*.** Since T73 it is a **base**
for a family of lock files -- `paths.gpu_lock_path(device_uuid)` appends the
hostname and the GPU UUID, so two machines never arbitrate each other's card and
tachi's two cards do not serialize against each other for no reason. Unset, the
base falls back to `paths.DEFAULT_GPU_LOCK` (a fixed file in the system temp directory). So a lane
that exports it and a lane that does not take locks in **different families and do
not exclude each other at all**, while both report having held a lock. Observed
2026-08-21 with three lock files live on roci at once: a pre-T73 literal path, the
current T73 derivation, and a third, older convention.

Export the same base in every lane. The stray files above are harmless once
everyone agrees on the base, but do not add a fourth.

**And a lock does not mean the card is yours.** Correctness work runs unlocked by
design, so `query_gpu_state()` legitimately reports a foreign process while you
hold the lock. That is not a lock failure; it is the protocol. What the lock
guarantees is that no *other quoted* run is competing.

`bench/worktree_python.sh` warns when either is unset. It does not set them --
`paths.py` keeps its default generic on purpose, and a script that injected a
machine path would get copied into something that ships.

**Rebuilding after a C++/CUDA change: this venv has no `pip`.** It is uv-managed.
`INSTALL.md` documents `pip install -e .` for a general reader, and that is right
for a general reader, but in the shared venv it fails with
`No module named pip`. Use:

```
uv pip install -e . --reinstall-package roshambo3
```

Two ways this bites, both observed 2026-08-21:

- **`pip install` "succeeds" while compiling nothing.** If you pipe its output
  through `grep`/`tail`, `$?` is the *filter's* status, not pip's, so the failure
  is invisible and the stale `.so` stays loaded. Check the artifact, not the exit
  code: `ls -l .venv/lib/python3.11/site-packages/roshambo3/_roshambo3_cuda*.so`
  and compare its mtime against your source change.
- **A stale extension fails like a code bug.** After merging a branch that touched
  `interface.cpp`, five colour tests failed with
  `this switch combination is not instantiated (key 29)` — which reads as T72's fix
  being absent or wrong. The fix was present in the source; the loaded `.so` was
  from the previous day. This is pitfall 1's family: the remedy is `rm -rf build`
  and a real rebuild, and the diagnostic is always to ask the *binary* what it
  contains rather than to trust that an install ran.
