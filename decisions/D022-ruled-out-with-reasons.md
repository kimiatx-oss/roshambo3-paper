# D022 — Approaches ruled out, with the reason, so they do not come back

**Date:** 2026-08-19
**Status:** active

Each of these was proposed, evaluated, and rejected on a specific ground. Recording them because
they are all *plausible* and will be re-proposed otherwise.

## Blackwell TMEM — not on this hardware

Verified on this toolchain:

```
tcgen05.alloc ... .target sm_120  -> error: Feature '.cta_group::1' not supported
tcgen05.alloc ... .target sm_100a -> assembles
```

TMEM is Blackwell **datacenter** (sm_100/sm_101) with 5th-generation tensor cores. The RTX PRO 6000
is **sm_120** and does not have it. Independently, TMEM is addressable only by `tcgen05` instructions
as tensor-core accumulator storage — it is not a general scratchpad, so it would not serve as
auxiliary storage even where it exists.

## Tensor cores for the coordinate transform — four independent blockers

The construction (block-diagonal A holding 4 transforms, B holding atoms in homogeneous coordinates,
8 atoms per `mma`) is dimensionally correct. It still fails:

1. **Structured sparsity does not apply.** Ampere 2:4 sparsity requires exactly 2 non-zeros per 4
   consecutive K elements plus a metadata operand consumed by `mma.sp`. Block-diagonal gives 4
   non-zeros per 16 in the wrong pattern. The multiply is fully dense; the zeros are waste, not
   skipped work. Even where 2:4 applies the ceiling is 2x.
2. **Precision.** Verified: there is no fp32 `mma` (`m16n8k16 ... .f32` -> "Unexpected instruction
   types"); `m16n8k16` is fp16/bf16 and TF32 is `m16n8k8`. 10-11 mantissa bits gives ~0.015 A at
   +/-30 A against the 0.001 A int16 quantisation we ship, itself checked against a 5.8e-4 gauge
   floor. Centring helps (~0.005 A) and is still 5x coarser.
3. **Fragment layout.** W = 4 lanes each own a different atom and each issues its own texture fetch.
   The `mma` D fragment scatters a 16x8 result across 32 lanes in a pattern that does not match
   "lane L needs atom L's transformed coordinates." Redistributing costs more than the 9 FFMAs saved,
   and costs it in SMEM or shuffles — SMEM being the resource being freed.
4. **Ceiling ~10%.** The transform is 9-12 instructions of ~35-40 in the atom loop; the atom loop is
   28% of warp instructions (42% after UPD = 2). A *free* transform buys ~10%.

`__ldcs` for L1 protection is likewise dominated by `__ldcg`: `ld.global.cs` (`LDG.E.EF`) allocates
an L1 line and marks it evict-first; `ld.global.cg` does not allocate at all.

## Method note that generalises

**Footprint comparisons between grains must hold the LANE BUDGET fixed, not the conformer count.**
The corpus is centred and principal-axis aligned, so the distinct-node union over resident
conformers is ~11x saturated — conformer count is nearly free, lane budget is not. Comparing
256 conformers x 4 starts against 256 x 1 (rather than 64 x 4, which is what W = 16 actually runs)
turned a free change into a 1.27x penalty. See `results/T35/CORRECTION-footprint-residency.md`.

## Rectilinear-sparse grids -- disjoint indexed rectangles instead of tiling all of space

Raised 2026-08-21 by the author, as an early idea never explored: rather than tiling the
query's bounding box, hold **disjoint rectangles and index into them**, on the
intuition that it would help color more than shape because a per-type color plane
has large empty regions.

**The sparsity is real and was measured.** T58 puts per-type plane occupancy at
**0.363**, and six separately padded per-type planes at **4.59x** the shape-only
bytes. Hydrophobe is 61% of all features; NegIonizable is absent from 91% of
molecules. So the intuition about empty space is correct.

**It is refuted anyway, twice, and neither refutation is about sparsity.**

**1. For shape, field bytes are not the working set. Measured.** T35's whole
finding is that the h = 0.5 collapse is *L1 residency of the sampled sub-volume*,
not L2 residency of the field. Its arm B varied the field from **0.468 MB to
1.586 MB (3.4x)** across query sizes 10 to 50 atoms and found the effect on time
was **at most 1.19x and not monotone -- the smallest field was the slowest cell.**
The working set is `V_sampled / h^3 x 8 B`, which a sparse layout does not change.
So the optimization attacks a quantity already shown not to bind.

**2. For per-type color, the binding constraint is the crossover, and storage
cannot move it.** T28 located where a grid stops beating an analytic sum: **21.8
query atoms** for the brick at h = 0.5 against the probe's analytic arm, and 5.2
for the texture arm at h = 0.8. A per-type color plane holds **~3.1 features on
average** (18.88 color atoms over six types) -- far below either crossover, and
Hydrophobe's ~11.5 is still below the brick's. The grid loses to the analytic sum
at that size **however the grid is stored**: sparsity reduces bytes per lookup, not
lookups. So the answer for color is not a sparser grid, it is **no grid** -- which
is the author's own second guess in the same message, and which `decisions/D025` now
records for a separate reason: the optimizer needs `dV_color/dpose`, an analytic
sum over 149.2 same-type pairs, and never needs the color field itself.

**The one version that is not refuted, and it is a different idea.** Nothing above
touches `V_sampled / h^3`. A representation that shrinks the *sampled sub-volume*
-- adaptive `h`, a tighter sampled region, per-bucket resolution -- attacks the
quantity T35 identified as binding. That is T41's territory, and T35's own
conclusion that "at production target sizes h = 0.5 is the wrong operating point"
says the operating point matters more than the layout. Anyone re-proposing sparse
grids should check whether they mean this instead.

> **Pointer updated 2026-09-09:** T41 is closed and this territory is **T137's**
> ("the per-width spacing policy has no scale term"). T137 also carries the reason
> the sweep could not simply have been run under T41's framing: the policy's
> functional form is wrong, not merely its constants -- the same table is right at
> 2M pairs and takes the field path from a 1.69x win to a 0.72x loss at 65,000.

**Reopening condition:** a measurement showing field *bytes* binding somewhere T35
did not look -- a much smaller L2 than roci's 134 MB is the obvious candidate,
and D006 notes tachi's 4.7 MB makes it the more representative platform for
grid-residency questions. T35 ran on roci.

### CORRECTION, same day: the field-bytes half of the argument above is withdrawn

The author pushed back and is right. The claim *"the working set is `V_sampled / h³ ×
8 B`, which a sparse layout doesn't change"* is wrong, and it cited the wrong T35
arm.

**Arm B, which I quoted, varied the field's total size** — query 10 → 50 atoms,
0.468 → 1.586 MB — and found ≤ 1.19×, non-monotone. That refutes "a bigger field
is slower". It says nothing about skipping lookups.

**The proposal was to skip them.** Bounding known-zero regions to zero removes the
fetch and the interpolation, which reduces *the distinct field bytes an SM's
resident conformers touch* — and that is precisely the x-axis of T35 §4's collapse
curve: **flat below 20 KB, 1.13–1.41× at 37–46 KB, 2.0–3.7× at 57–61 KB, 9.0× at
131 KB, against a 64 KB L1.** Two other arms confirm the mechanism from opposite
directions: **arm D** halved bytes per node (float4 → half4) and moved the knee by
one sweep point, ≈1.2× in `h`; **arm A** varied L1 capacity alone and got
**6.16× at h = 0.5**. So sparsity acts on the binding resource, with a gradient
between 1.2× and 9× depending on where the working set already sits.

**What still rules the idea out for color is the crossover, and only that.** T28
put it at 21.8 query atoms (brick, h = 0.5) and 5.2 (texture, h = 0.8) against an
analytic arm. A per-type color plane holds **~3.1 features on average**; even
Hydrophobe's ~11.5 is below the brick's. Below crossover there is no grid to make
sparse — the analytic sum wins outright, which is where `decisions/D025` lands from
the gradient side. The single-plane all-type field is above crossover at 18.9
features but cannot represent per-type widths and prefactors, which is the original
`doc/ARCHITECTURE.md` objection and stands.

**So: ruled out for color on crossover, not on memory. Not assessed for shape**,
where arms A/C/D say the mechanism is real and nobody has costed a sparse
representation against it.

### Where the sparsity does pay, measured: per-tile type presence

The intuition was right about empty space; it shows up as **warp divergence**, not
as bytes. `tickets/T63/tile_divergence.py`, over T58's real per-type counts, tiles
of 32 as the corpus lays them out (sorted on `n_real`):

| tier | conf/mol | total-color waste | at real tile composition | cost of per-type dispatch | NegIonizable waste | tiles with no NegIonizable |
|---|---:|---:|---:|---:|---:|---:|
| D5 | 9.48 | 1.278× | **1.136×** | 1.829× | 10.12× | 32.6% |

Three findings, all new:

1. **Coalescing on `n_real` costs only 1.28× on the total color count**, and
   **1.14× at real multi-conformer tile composition** — because all conformers of
   a molecule share its feature counts, so a D5 tile spans ~4 distinct molecules
   rather than 32. At higher conformer counts per molecule it approaches 1.0. So
   re-sorting or scatter/gather on color count is **not** needed, which answers the
   question that prompted this. It is also a reason to keep a molecule's conformers
   contiguous in the tile, which the builder already guarantees.
2. **Per-type dispatch costs 1.83× the tile's mean total**, because each
   type's maximum is hit by a different lane and the tile pays the sum of maxima.
   That is an argument against per-type dispatch that T58 did not have, and it is
   independent of its bytes argument (4.59× at occupancy 0.363).
3. **A per-tile, per-type presence bit is free and worth taking.** NegIonizable is
   absent from every lane of **33% of tiles**; skipping the segment entirely
   costs one ballot. This is the actionable form of "bound the empty regions to
   zero" — applied to the tile rather than to space.

### The query-side bitmap is the useful one, and I framed the tile side too favourably

The author's extension -- keep the type-presence bitmap for the **query** too, and skip
any plane that can only have zero query overlap -- is the stronger half, and for a
structural reason: a screen has one query set and thousands of blocks, so a type
the query lacks contributes zero to **every pair in the entire run**. The bit is
hoistable out of the whole screen, not out of a tile.

Measured, `tickets/T63/type_presence_skip.py` over T58's real per-type counts:

| tier | live segments of 6, query bit | tile bit | both ANDed | same-type pair **work** retained |
|---|---:|---:|---:|---:|
| D5 | **4.12** | 5.64 | 4.08 | 0.9874 |

`P(type present in a molecule)`: Hydrophobe 0.997, Acceptor 0.955, Aromatic 0.902,
Donor 0.854, **PosIonizable 0.324, NegIonizable 0.093**. A molecule carries **4.12
of 6 types** on average.

Three conclusions, one of which corrects the entry above.

1. **The query bitmap cuts segment visits by 31%; the tile bitmap by about 6%.** My
   "per-tile presence bit is free and worth taking" was true but overstated as the
   win. A tile's bit is a **max over 32 lanes**, and with five of six types present
   in >85% of molecules that max almost always finds every type -- so the tile bit
   fires mostly for NegIonizable and little else. ANDing the two adds ~0.04
   segments over the query bit alone. **Take the query bitmap; the tile bit is
   nearly free but nearly worthless.**
2. **Neither saves arithmetic: 98.74% of same-type pair work survives both bits.**
   The types that skip are exactly the rare ones that carry no work -- T58 put the
   two ionizable types at 0.11% of same-type work, while Hydrophobe is 88% of it
   and is present 99.7% of the time. So the value is **entirely per-segment
   overhead and divergence**, not FLOPs.
3. **Which makes it a real win only if per-segment overhead is significant** --
   loop setup, bounds computation, the warp-wide max, register pressure. T58
   already flagged that its S4 segments are short and that this needed measuring;
   with 4.12 live segments over 18.88 features the mean segment is ~4.6 features
   long, so the overhead fraction is plausibly large. **T63 must measure it rather
   than assume it either way** -- the bitmap is cheap enough that the only reason
   not to take it is if segments turn out not to cost anything to enter.

## The exponential map on the field kernel -- not worth a ticket, and the precondition it removes is smaller than believed

T45 asked whether adding an `OPT` template parameter to `optimize_pairs_field`
deserves its own ticket. **No.** Every argument for it is negative, structurally
unavailable, or smaller than it looked:

- **The production kernel has no `OPT` parameter at all.** The exponential map
  exists only on the analytic kernel, shipped cell. T45 also found that the
  ticket's stated work item -- "instantiate `OPT` for the dense and threadwise
  paths" -- names code that **was never ported**.
- **The only measurement on the grid path is a loss.** T17 §7.1/§9's −2.6%/step and
  101 -> 88 registers are the *analytic* path; §7.2 measured the grid path at
  **+3.9%/step**. On a probe, so per D015 the production price is unmeasured -- but
  the sign of the only evidence is against.
- **The register win cannot transfer.** The field kernel's shipped configuration is
  pinned at **exactly 64 registers/thread** by `__launch_bounds__(256, 4)` --
  1024 threads x 64 is the whole register file. The count is a constraint there,
  not an outcome. `UPD == 2` also spreads the pose across lanes, which a quaternion
  product cannot use.
- **Recall is a tie** (0.9852 vs 0.9851).
- **And the precondition it would remove permits 24 rotations, not 3.** The
  signed-permutation condition admits every proper signed permutation -- the
  **octahedral group, 24 elements**. So "the exp map makes start modes free to be
  arbitrary rotations" is a smaller prize than it reads: a richer *discrete* start
  set is already legal. What genuinely needs the exp map is a start set off that
  group -- T18's inertia-eigenvalue-gap frames, or anything continuous or learned.

**Reopening condition:** T40 producing a start set that wants off-octahedral
rotations, or a measurement of the exp map on the *production* field kernel rather
than on T17's probe.

### Correction: the stated reason for withdrawing the 120 degree offset was false

T45 caught this and it is worth recording because the false reason was propagated
by me, from the implementor's note, into T45's own ticket text.

The note said a 120 degree rotation about (1,1,1) "is **not** a signed permutation,
so Adagrad's per-component cache would no longer commute with the conjugation and
the exactness proof would fail -- silently." **It is a signed permutation.** It is
the 3-cycle x -> y -> z, i.e. the matrix

```
[ 0 0 1 ]
[ 1 0 0 ]
[ 0 1 0 ]
```

with `det = +1` and every entry within **2.2e-16** of {0, ±1}; T45 measured the
worst miss over the whole proposed coset at **1.788e-07**, i.e. float32 noise. The
tetrahedral group is a subgroup of the octahedral group, which *is* the 24 proper
signed permutations.

**The withdrawal stands, on the other reason already given**: the conjugation
reparameterization already removed the singularity the offset was proposed to fix,
so it solves a solved problem. T45's assertion deliberately **accepts** this coset,
with a test pinning that, because accepting it is correct.

### WITHDRAWN, same day: the exponential map goes back on the table

The author reopened this and is right. The entry above conflated a throughput
measurement with an optimization-quality question, and cited a tie that T17
itself explains as an artifact.

**What the entry got wrong.**

1. **"Recall is a tie" is not evidence about the parameterization.** T17 §7 says
   so in its own voice: *"with `start_mode = 1`'s four pi-flip starts, the
   optimiser rarely has to travel far in rotation from whichever start it began
   at, and **the defect the exp map fixes does not bite. Remove that cover and it
   does**."* Its `start_mode = 0` table, everything else equal:

   | steps | additive | exp map | delta |
   |---|---:|---:|---:|
   | 25 | 0.2675 | 0.2698 | +0.0023 |
   | 50 | 0.2833 | **0.2956** | **+0.0123** |
   | 100 | 0.3025 | **0.3173** | **+0.0148** |
   | 200 | 0.3181 | 0.3290 | +0.0109 |

   T17's summary: *"it moves in the predicted direction, by the predicted
   mechanism, and by more the longer the optimiser runs."* The four-start tie is
   **cover**, not a null.

2. **+3.9%/step is a throughput number and does not answer an optimization
   question.** The entry used it as though it did.

3. **The register argument was overstated.** `__launch_bounds__(256, 4)` pins 64
   registers/thread because *someone chose 4 blocks/SM*. If the exp map frees
   registers, relaxing to 3 blocks/SM is a tuning experiment, not a wall.

4. **"There is no `OPT` parameter" is an engineering cost, not evidence.** It says
   the work is larger than the ticket claimed. It says nothing about whether the
   change is right.

**And the mechanism is not in dispute.** `kernels.cu:788-790`: the additive update's
applied rotation is *"a POSE-DEPENDENT linear map of the step, shrunk by
~cos(theta/2) along v and rotated by the -d x v term."* The exponential map is a
uniform tangent-space step. A smoother, pose-independent parameterization being
*worse* at optimization would be the surprising result, and nothing measured says
it is.

**The reframing, and the question nobody has asked: the exponential map and the
start set are substitutes.** Four pi-flip starts exist partly to keep every
trajectory near identity so the shrinkage never bites. If the exp map removes the
need for that cover, **fewer starts may suffice at equal recall** -- and
`start_mode_n = {1, 4, 10}` means four starts is four optimizer trajectories per
pair. T18 measured that **97.9%** of gold top-1e5 hits are found by exactly one
start mode; that is consistent with the starts genuinely exploring distinct basins
*or* with them compensating for a parameterization that cannot travel, and **nobody
has distinguished those two readings.**

**Sequencing, which is what makes this cheap.** `OPT` already exists on the
**analytic** kernel. So the accuracy claim can be tested there with **no new
code**, before paying for the field-kernel port: sweep `opt_mode` x `start_mode` x
steps and ask whether the exp map at fewer starts matches the additive rule at
four. If it does, the port is justified by throughput rather than by elegance. If
it does not, nothing was spent. **T45 owns this**, re-scoped accordingly.

---

## `__ldcs` as a residency tier -- ruled out on both channels, 2026-08-22 (T78 round 2)

**What it was.** `CoordResidency.GLOBAL_LDCS`, added by T78 round 2 because
`grep` found no `__ldcs`, `__ldca` or `__ldcv` anywhere in the CUDA sources --
the load-hint axis had exactly one non-default point on it (`__ldcg`), so its
shape had never been established. `__ldcs` allocates an L1 line but marks it
**evict-first**; `__ldcg` declines to allocate one at all.

**Two framings, both tested, both lose.**

*Streaming.* The campaign plan's sentence -- "shape makes one linear pass per
library atom per step, so a streaming hint suffices" -- reads as an argument for
evict-first on the shape channel. The author predicted the opposite, that `__ldcg`
would beat `__ldcs` on shape, because *one pass per step* is not *read once*:
each row is re-read 25 steps x 4 starts, a row is at most ~1.8 KB, and L2 serves
that reuse distance. **Neither prediction held.** At shape `S = 2`, everything
else equal (`results/T78/r2_shape_residency.json`):

| shape residency | kernel (ms) |
|---|---:|
| `GLOBAL` (an ordinary cached load) | **3,278.9** |
| `GLOBAL_LDCS` | 3,448.6 |
| `GLOBAL_LDCG` | 3,456.6 |

The two hints tie -- 0.23% apart against a ~0.3% run-to-run floor -- and **the
ordinary load beats both by 5.2-5.4%.**

*Cache partitioning.* Its remaining argument in a two-channel kernel is that a
non-polluting load can protect the OTHER channel's residency. Also measured, on
the channel whose data is cheapest to re-fetch, and it also loses: shape
`__ldcs` beside plain color is 3,448.6 ms against 3,278.9 for plain beside
plain, and color `__ldcs` beside plain shape is 2,969.1 against 2,943.2
(`results/T78/r2_refine.json`).

**The mechanism, measured rather than argued.** `results/T78/r2_ncu_summary.json`:
against the same cell, color `__ldcg` drops the **L1 sector hit rate from 80.90%
to 72.56%** and issue activity from 32.12% to 25.01% while the L2 hit rate
barely moves. Both channels have real **inter-step** reuse -- a slot is re-read
100 times per pair at 25 steps and four starts -- and the ordinary cached load
is already the right policy for it. A hint that declines the L1 line costs 3.10x
on color; a hint that marks it evict-first costs a few percent. Neither buys
anything back.

**Standing.** The enum member stays so that the results files above remain
readable, and it must not be offered as a shipping option. Its ~50
instantiations are one line of `tickets/T78/r2_patch10_dispatch2.py` to remove.

**Reopening condition.** A kernel where the two channels' working sets actually
compete for L1 -- which this one's counters say they do not, at 81% L1 hit rate
and 0.63% texture-pipe utilization at the chosen cell -- or an architecture
whose L1 is small enough that one channel evicts the other. Measure the hit rate
first; if it is already high, there is nothing for a partitioning hint to buy.
