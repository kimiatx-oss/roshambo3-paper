# D009 — How to claim a GPU bottleneck

**Date:** 2026-08-16
**Status:** active, permanent
**Raised by:** the author, reviewing T10's attribution
**Applies to:** every ticket that profiles a kernel or claims something is "X-bound"

## The rule

**Do not claim a bottleneck from warp stall-reason shares.**

`selected` and `not_selected` are **not stalls**. `not_selected` means a warp was *eligible and
lost scheduler arbitration to another warp*. NVIDIA's triage guidance is explicit on this point.
A large `not_selected` share means there are plenty of ready warps — it is evidence **against**
latency starvation, and says nothing on its own about instruction-throughput saturation.

**Claim a bottleneck from `smsp__issue_active`, `sm__inst_issued`, and the dominant execution
pipe.** Report those for every variant measured.

**Causal ablation outranks every counter argument.** "I reduced X and runtime fell by Y" is the
strong evidence; counters explain *why*. Where both exist, state whether they agree — a
disagreement between them is itself a finding and must be reported, not reconciled silently.

## The case that produced this rule

T10 concluded the kernel was "instruction-issue bound" from `not_selected` dominating stall
cycles at 28%. It had also collected `smsp__issue_active` and not reported it:

| counter (shipped kernel) | value | its own idealised loop |
|---|---|---|
| `smsp__issue_active` | **66.9%** | 86.4% |
| FMA pipe | 49.7% | 73.1% |
| **LSU pipe** | **45.1%** | 21.5% |
| XU pipe | 14.8% | 21.5% |
| ALU pipe | 7.8% | 2.8% |
| warps active | 33.3% | 86.0% |

A third of issue slots are unused. Issue is the largest single factor, not a ceiling.

## The second error: "high L2 hit rate makes excess sectors free"

It does not. A 99.8% **L2** hit rate explains why extra sectors are not expensive DRAM traffic,
but they still consume **L1TEX wavefront capacity, XBAR and L2 bandwidth, L2 sector throughput,
and return bandwidth**. NVIDIA treats low-DRAM/high-L2 as potentially **L2-bound**, and
uncoalesced access as potentially **L1TEX/wavefront-bound**.

Two specifics that were misreported: the **L1** sector hit rate is **86.7%**, not 99.8% (that was
L2); and LSU sits at **45.1%** against FMA's 49.7%, so 31.95 sectors per request is doing real
work on the memory pipe.

## The corrected diagnosis, and what it predicts

> The kernel is **co-limited by FMA-pipe and LSU-pipe issue** (49.7% and 45.1% of peak), with
> overall issue-slot utilisation at **66.9%**. There is no single clean bottleneck.

This reconciles T10's "fixing coalescing is worth only 3.9%" ablation with the objection instead
of choosing between them: removing scattered access halves LSU pressure, FMA then becomes
binding, so the *marginal* gain is small even though the sectors were never free.

**Testable consequence: attacking LSU and FMA together should be worth more than the sum of the
individual ablations.** That is the shape of a warp-per-pair / lane-per-atom grain change (T14),
and T13's instruction-count reduction is the causal test of the issue-bound component.

## What survives from T10 unchanged

Occupancy is nearly exhausted (8→16 warps 1.23×, 16→32 only 1.09×, 48 *worse* than 32); the loop
issues 36 SASS instructions per `MUFU.EX2`; and the "10× transcendental headroom" was a
percent-of-peak normalised at a clock nobody was running at (see `decisions/D007`).


---

## Confirmed and sharpened by T14 (2026-08-16)

T14 built the grain sweep this correction predicted, and both halves of the co-limited picture
hold. Measured on the shipped binary under `ncu`:

| | blockwise (shipped) | W=2 | W=32 |
|---|---|---|---|
| **L1TEX throughput %** | **68.9** | 54.4 | 53.3 |
| FMA pipe % | 51.6 | **61.8** | 49.8 |
| `smsp__issue_active` % | 69.5 | **83.7** | 77.4 |
| sectors / request | 31.92 | **15.93** | 12.28 |
| thread instr / apg | 38.41 | 40.08 | 73.22 |

**L1TEX at 68.9% is the highest-utilised pipe in the shipped binary — above FMA.** The
"coalescing is a trap" claim was wrong, and the mechanism is now clear: any W ≥ 2 coalesces
`molB` perfectly, and *that* is the win; the grain itself only ever costs instructions.

**T10's decomposition is re-priced.** Its "scattered `molB` — 1.04×" becomes **1.16×** on the
gradient loop, ~4× upward. T10's figure came from an ablation on the **idealised** loop, where
L1TEX has nothing else to do, and does not transfer to the real kernel. **A single-factor
ablation performed on a stripped-down variant is not a valid price for that factor in the full
kernel** — add that to the method.

Fixing memory alone then caps out quickly, exactly as predicted: FMA becomes binding at 61.8%.

Counter and causal ablation agreed to ~1% (`sm_cycles/apg` gives 1.157× for W=2 against
1.148–1.163× from independent locked-clock timing), which is what D009 asks for and is the
strongest form of the evidence.


---

## RESOLVED by T13 (2026-08-16) — the kernel is L1TEX-bound, not issue-bound

T13 ran the causal test this decision asked for, and it settles the question.

Cutting the shape gradient loop from **36.00 to 25.75 SASS instructions per atom-pair-gradient**
(a 1.398× instruction reduction) moved runtime only **1.094×** — about **27% conversion**. If the
kernel were issue-bound the conversion would approach 100%.

The counters say why, and they move in the opposite direction to the issue-bound story:

| | before | after the instruction cut |
|---|---|---|
| `smsp__issue_active` | 70.2% | **58.3%** (falls) |
| L1TEX | 69.5% | **75.2%** (rises) |
| FMA | 52.1% | 39.5% |
| LSU | 46.1% | 46.2% |

**The limiter is L1TEX.** Removing instructions frees issue capacity that the memory path cannot
use. Occupancy was invariant across all six arms (33.17–33.18%), registers 99–102.

Counter and ablation agreed to **0.03–1.8%**, two `ncu` runs an hour apart agreed to four
significant figures, and the `blockwise` row reproduced T14's to within 1% on every metric — so
this is not a measurement artefact.

**Superadditivity confirmed**, as this decision predicted: tile + hoist together give **1.394×**
against **1.230×** for the product of the individual ablations, with the cross-term at 15% of the
total. **Stop writing T10's gap decomposition as a product of independent factors.**

### Coalescing is closed, not merely reopened

T13 built a **planar** tile reaching **3.99 sectors per request** — fewer L1TEX wavefronts than
the best point of T14's entire grain sweep — and it is **1.5% slower**. So the memory path has
been driven to its floor and the remaining L1TEX pressure is not addressable by layout. The
question the author reopened is now answered in both directions: the sectors were never free (T14),
and eliminating them entirely does not pay (T13).

### The method held up

Three tickets reached three different answers about the same kernel — "issue-bound" (T10),
"co-limited FMA/LSU" (D009 after the author's correction), "L1TEX-bound" (T13) — and each revision
came from **preferring a causal ablation in the real kernel over a counter argument or a fit**.
T14's 1.22× projection failed because it priced instructions and sectors as independent additive
costs; T10's 1.04× failed because it ablated on an idealised loop. **Ablate the real kernel, and
do not fit a model across factors that interact.**


---

## Scope correction 2026-08-17 — L1TEX-bound is the ANALYTIC kernel; the grid is unattributed

Raised by the author. The "L1TEX-bound at 75.2%" result is T13's, measured on
`optimize_sparse_blockwise` and its tile/xhoist variants — **the analytic kernel**. It was then
repeated in a project summary as though it described the current limiter generally. It does not.

**The grid kernel has never been counter-attributed.** T15 queued
`tickets/T15/run_ncu.py` → `results/T15/ncu_grid.json` behind a sibling's GPU lock; the file does
not exist and both agents died before it ran. It cannot be moved to tachi — `ncu` counters are
unavailable there, since `decisions/D005`'s fix was applied on roci only. **Timing and accuracy
move between machines; attribution does not.**

### What we do know about the grid path, from causal ablation alone

T15's evidence stands on its own and per this decision the ablation outranks counters anyway:

- Replacing 21–45 `exp2f` pair terms with **one 16-byte fetch** makes the loop **3.6–5.4× cheaper
  per step**.
- **At W = 1 the grid is a *loss*** on both machines (0.40–0.50× against the best analytic grain).
  One scattered, dependent `LDG.128` per atom, with nothing to hide it, is worse than 21 `exp2f`
  with plenty of ILP. **The grid trades arithmetic for a dependent scattered load, and the trade
  only pays once enough samples are in flight.** That is a *latency* story, not the analytic
  kernel's throughput story.
- Any W ≥ 2 coalesces `molB`; **W = 4 is the optimum**, W = 16–32 a loss on both machines.
- Per-step cost is **nearly independent of h** (0.354 ms at h=0.5 vs 0.252 at h=0.8) but
  **strongly dependent on grain**, because the per-step reduce-and-Adagrad block issues once per
  group-iteration and there are W times as many per conformer. **Atom-loop work is W-independent;
  per-step overhead is W-linear.**

### The inference that follows, and it is strategically significant

The grid shrinks the atom loop by roughly **20×**, so **the per-step reduce-and-Adagrad overhead
becomes proportionally dominant on the grid path in a way it never was on the analytic path.**

If that holds, **reducing the step count is worth far more on the grid path than on the analytic
one** — which reframes T17. T24 measured 25 steps at ~3× the throughput of 100 with a real
accuracy cost that was judged too expensive under the old bit-identity bar; under `decisions/D013`
that judgement is due for revisiting anyway, and on the grid path the payoff is larger than the
number T24 measured on the analytic kernel.

**This is an inference from the grain sweep, not a measurement. It needs the queued `ncu` run.**


---

## RESOLVED again by T27 (2026-08-17) — the analytic kernel is no longer L1TEX-bound; it is issue-bound at 88%

T13's "L1TEX-bound at 75.2%" was correct for the kernel it measured. **T27 moved the
limiter off memory**, and the scope correction above is now superseded on the analytic
side by a measurement rather than by a caveat.

### The analytic path

| | T13's `tiled_xhoist` (the baseline T27 inherited) | T27's best arm |
|---|---|---|
| `smsp__issue_active` | 75.6% | **88.0%** |
| dominant pipe | LSU 59.8% | **FMA 60.5%** |
| L1TEX | 59.8% | **31.0%** |
| L2 | 17.6% | **4.4%** |
| SM cycles / apg | 0.001638 | **0.001247** (1.313×) |

**88.0% is the highest `smsp__issue_active` recorded anywhere in this project.** The
analytic kernel is now **issue-bound with FMA the dominant pipe**, and the next kernel
ticket should target arithmetic and ILP, not memory.

### Three memory ablations, all negative, and the memory path is closed

| ablation | what it changed | worth |
|---|---|---|
| planar tile (T13) | sectors/request 31.92 → **3.99**, the hardware floor | **0.985×** (slower) |
| `qvec` (T27) | L1TEX requests/apg 0.0849 → **0.0313**, LSU 59.8% → **24.3%** | **0.986×** (slower) |
| staging (T27) | global requests/apg **160× fewer**, sectors/apg **342×**, L2 → 4.4% | 1.08–1.13×, **via latency only**, and forfeit the moment it costs a warp |

**Sectors, requests and global traffic have each been driven to or near their floor and
none of them is the constraint.** A future ticket should not re-derive this.

### What T27 adds to the method

**Distinguish a throughput cut from a dependency-chain cut, because they convert at
completely different rates on the same kernel.** T13 measured `xhoist` — which removes
*parallel* work — converting instruction cuts at **27%**. T27's `nw` removes two
multiplies that sit on the serial chain between `MUFU.EX2` and the accumulator: a
**9.7% instruction cut returning 14–17%**, i.e. **over 100% conversion**. Instruction
count alone does not predict the win; where the instruction sits in the recurrence does.

**A "request" and a "wavefront" and a "pipe %" are three different quantities and the
kernel can be limited by none of them.** T13 read `l1tex__data_pipe_lsu_wavefronts` as
one number and attributed all of it to target traffic. Splitting requests
shared-vs-global (`smsp__inst_executed_op_shared_ld` against `..._global_ld`) showed
**94% of this kernel's L1TEX load requests were the *query*, not the target** — and
that cutting them 2.7× buys nothing.

**Disassemble before attributing.** The shape gradient loop contains **zero `LDG`**.
One `cuobjdump` run, costing no GPU time, refutes the premise three tickets shared.

### The grid path — now attributed, and the inference above does not survive

T27 ran the queued `ncu` job on roci (`results/T15/ncu_grid.json`,
`ncu_grid_steps.json`, findings in `results/T15/NCU_FINDINGS.md`). **The grid path is
latency-limited**, and emphatically: at h = 0.5, W = 4 it cuts warp instructions per
optimiser step **2.52×** against the analytic probe and cycles only **1.09×** — **6%
conversion** — with `issue_active` at **38.7%**, dominant pipe 18.3%, and
`long_scoreboard` at **72.8%** of stall cycles (94.8% at W = 1). Nothing on the grid
path is saturated; it is waiting on a dependent brick fetch.

**Two corrections to the inference this decision recorded as needing the `ncu` run:**

1. **The per-step reduce-and-Adagrad block is not where a grid step goes.** That would
   show as `barrier`/`wait`/`not_selected`; `wait` is 10.3% while `long_scoreboard` is
   72.8%. The residual after the atom loop shrinks is **the fetch**.
2. **Step-count reduction is worth the same on both paths, not more.** Profiling every
   configuration at two step counts removes the fixed per-launch cost by construction,
   and it is **0.1–0.4% of a 100-step launch on every configuration, analytic and grid
   alike**. Cost is essentially linear in steps everywhere, so 100 → 25 is worth ~4× on
   both. **T17 should not be reframed on this basis.**

**What does have headroom on the grid path is memory-level parallelism**: the same
kernel at h = 0.8 has the same instructions per step (172.0 M vs 172.1 M) and **1.96×
fewer cycles**. The lever is bricks in flight, not fewer steps.


---

## Addendum from T31 (2026-08-17) — a counter that correlated with a win is not a control knob

T28 measured the texture path's rate tracking **sectors per warp request** (`half4` 15.7 against
`float4` 45.0) and concluded "sectors dominate". T31 tested that as a *lever*, by reordering the
target atoms so the four cooperating W = 4 lanes fetch spatially adjacent atoms, with the **SASS
held byte-identical** — a pure data permutation, which is the strongest form of the causal ablation
this decision asks for.

| stored → greedy-quad ordering, `tex4hnb`, staged, carveout 50 | h = 0.5 | h = 0.8 | h = 1.2 | h = 2.0 |
|---|---|---|---|---|
| sectors / warp request | 16.70 → 16.40 | 15.65 → 14.05 | 14.02 → 11.51 | 11.46 → 8.83 |
| | −1.8% | −10.2% | −17.9% | **−22.9%** |
| **cycles ratio** | 1.0059× | 1.0038× | 1.0009× | **1.0033×** |

**A 1.30× cut in sectors per request bought 1.003×.** T28's win was real, but it was not *bought
with* the sector cut alone: the same change deleted 67.8 thread instructions per sample and halved
the field. **Do not treat a counter that moved alongside a win as a knob until you have checked that
its resource is still scarce.** The check is one `ncu` cell.

**What the grid kernel's limiter is now**, and it supersedes the "memory-level parallelism is the
headroom" line above for the *shipped* configuration: `tex4hnb`, h = 0.5, staged, carveout 50 runs at
**`smsp__issue_active` 79.4%, no pipe above 31%, L1 sector hit 97.2%, L1TEX 61.5%**. T27 measured
38.7% issue and 72.8% `long_scoreboard` on the unstaged, unpartitioned grid arm; **staging plus the
carveout (`decisions/D016`) closed that**, and what is left is issue-limited with no single pipe to
attack.

**A second, cheaper method note.** T31's whole result is one CPU statistic: at h = 0.5 the four
atoms a warp-quarter fetches touch **31.997 distinct grid nodes as stored and 31.985 under the
tightest possible grouping**, out of 32, because a bond is 1.4 Å and a cell is 0.5 Å. **Price the
geometry before building the optimisation.** The mechanism was right about *where* it would act — a
texture request in L1TEX is exactly the aligned atom 4-tuple, measured to within 1.6e-5 of the
predicted request count — and wrong about the scale by 3×, and only the arithmetic separates those.
