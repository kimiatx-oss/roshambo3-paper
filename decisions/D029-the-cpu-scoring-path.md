# D029 — The CPU scoring path: the frame, the oracle, and what may be compared

**Date:** 2026-09-02
**Status:** **accepted 2026-09-02 by the author.** Section 3 is decided as
proposed; section 4 is the author's addition and is the part that owes work.
**Source:** `results/T119/`, ticket T119
**Constrains:** every CPU kernel arm in T121-T126, and every comparison between
a CPU number and a GPU one

## Why this exists

ROSHAMBO3 now has a second scoring backend. Four questions have to be settled
before T122 starts producing arms, because each of them changes what those arms
may be measured against. Two are already answered elsewhere and only need
stating in one place; the third needed a decision and has one; the fourth came
out of making the third.

## 1. The CPU path adopts the reduced-overlap frame, as a declared change

Not discretionary. `doc/NUMERICS_POLICY.md`:85-99 legislates this exact case:

> the reduced-overlap frame of §4 was applied to the CUDA kernel and
> **deliberately not** to the C++ backend. … The C++ backend keeps volume units
> and stays an oracle held to `rtol=1e-4`. **If it is ever promoted to a
> scoring path, it must adopt the canonical frame first, as a declared change.**

T119's kernel does: coordinates pre-multiplied by
`COORD_SCALE = sqrt(alpha log2 e) = 0.77687365`, the inner term exactly
`exp2(-|delta|^2)`, the prefactor applied once at reporting, the gradient
divided by `S_AA + S_BB` inside the accumulation, and `lr_t` in scaled Angstrom
on the way in with `t` divided by it on the way out. The compiled-in constants
are checked against `numerics`' derivation
(`results/T119/oracle_agreement.json`), so the two cannot drift.

## 2. The oracle is `roshambo3.reference`, never the CUDA kernel

Pitfall 5, and it is not hypothetical: *"C++ and CUDA agree, so the math is
right — they agree because they share the typo"*, and a quaternion
normalization defect survived in ROSHAMBO2's two backends for exactly as long
as they were each other's only check.

So T119's kernel was derived from `reference/overlap.py` and the published
expression. The CUDA source was read for **conventions** — which molecule the
pose applies to, what the start set is, where the scale lives — and not for the
algebra. Measured against the float64 oracle: worst relative error **7.6e-7** on
`V_AA`, **5.2e-7** on `V_AB`, Tanimoto absolute **2.1e-7** over 40 pairs.

**This survives contact with the CUDA kernel being *available* to check
against.** Agreement with it is evidence about the port, not about the
mathematics, and a future CPU arm that validates only against the GPU has
re-created the defect this rule exists to prevent.

## 3. A CPU score is a function of the vector width, and comparison is on ranked output

This is the one that needs a decision rather than a restatement.

`doc/NUMERICS_POLICY.md` §2's rule is *"a change to **where** a value lives is
free; a change to **when** it is added is not"*, and lists a reordered reduction
among the six axes that all reach the same saturated output distribution as
`--use_fast_math`. **A vectorized sum is a reassociation**: an AVX2 arm
reducing 8 partial sums and an AVX-512 arm reducing 16 do not produce the same
float, and neither reproduces the scalar kernel's source-order accumulation.

There is no way around this that keeps the width. An arm forced to reduce in
scalar source order regardless of width forfeits most of what the width buys.

**The proposal.** Accept it, on the precedent that is already load-bearing:

* **D001/T25 measured exactly this situation across two GPUs** and accepted it.
  Volta against Blackwell, identical source and bit-identical inputs: only
  **0.12%** of pairs bit-identical after 100 Adagrad steps, |dT| p99 **2.6e-5**
  — and top-1 and top-5 set *and order* identical for **480/480** queries, with
  a merged top-N across the two reproducing the homogeneous list exactly.
  Bitwise comparison across architectures was then **forbidden as an acceptance
  criterion**. A CPU ISA is one more architecture, and the mechanism is the same
  one: the optimizer amplifies a last-bit perturbation that the scoring
  arithmetic does not.
* **D013 already makes acceptance recall and top-end ranking**, on the author's
  stated position that bit-exactness is too stringent a criterion and that the
  end goal is correct recall and top-end ranking.

**What that requires in exchange, and it is not optional:**

1. **Every CPU run record carries the ISA and the vector width**, exactly as it
   carries `cuda_architectures`. T118 built the slot and refuses a
   decision-grade CPU number without the *selected* dispatch target — asking
   the binary what it contains being a different question from asking the
   process what it chose.
2. **Two CPU arms at different widths are compared on ranked output**, never
   bitwise, and a record that does not name its width cannot be compared with
   anything.
3. **Tier 3 remains the specification and it remains the CUDA kernel's.** The
   CPU path computes the same function; it is a second implementation, not a
   second specification. Where a reported number must come from one place, it
   comes from there.
4. **A width change is a declared numerics change** and is measured on ranked
   output before it ships — the same gate `xhoist` and int16 staging passed.

## 4. The anchor is a reference implementation, not either optimized one

**Added by the author on accepting section 3**, and it closes a gap section 3 makes
visible rather than creates.

If a CPU score legitimately depends on vector width and a GPU score legitimately
depends on architecture, then **neither optimized implementation can be the
reference for the other**, and today each is effectively its own: the GPU's only
portable bit-level check, `tests/data/golden_scores.npz`, is generated **by the
GPU** and gated on its architecture list, so it cannot anchor a CPU arm at all —
and T128 found it has not been anchoring the GPU either, having silently skipped
since T106 on every `native` dev build.

That is pitfall 5 at the scale of the project rather than of a function: two
implementations that agree because they were checked against each other.

**So there is a third thing, and both optimized paths are measured against it:**

* **A stamped reference scalar implementation.** T119's CPU kernel is the
  candidate — it already runs the shipped schedule in the canonical frame with
  source-order fp32 accumulation, which is the accumulation every vectorized arm
  reassociates *from*. It is frozen and stamped: the source hash, the constants,
  the settings, the seed.
* **Stamped reference results generated by it**, which the GPU and every
  optimized CPU arm compare against — replacing, for portable purposes, a
  fixture generated by one of the things being checked.

**The anchor is held at a declared tolerance and on ranked output. It is not a
bitwise object.** This was drafted the other way and the draft was wrong, in the
same way section 3 was nearly wrong: a bitwise-portable anchor would need its
own pinned polynomial `exp2`, because `std::exp2` is libm's and differs across
platforms and versions — but **a change of `exp2` implementation is a far larger
numerics change than a reassociation.** It is squarely in the class T24
enumerated, where every perturbing axis lands on the *same* saturated output
distribution, so it has to be judged on recall no matter what. Demanding
bitwise portability would therefore buy a property nobody would then use, and
pay for it by constraining the reference's implementation and by making the
anchor wait on T121.

So the anchor is an **oracle at a declared tolerance**, which is exactly the
standing `reference/overlap.py` is already held to (`rtol=1e-4`), one level up.
What makes it an anchor is not bit-exactness; it is being a **third
implementation with a frozen algorithm and a stamp**, which is what neither
optimized path can be for the other.

Three properties it must have:

1. **Frozen and stamped**, so a fixture can name what produced it: the source
   hash, the constants, the settings, the seed — **and the platform and libm**,
   precisely because the results are not claimed portable.
2. **Generated once and committed**, so both optimized paths compare against the
   same numbers rather than each against its own re-run.
3. **Not a second specification.** Section 3's item 3 stands unchanged: Tier 3
   remains the specification and it remains the CUDA kernel's. The anchor is
   what two implementations are *compared* against; it does not become the
   source of a reported number.

**Bitwise comparison keeps a role, and it is the narrow one it always had:**
*within* one implementation, on one platform, across a change that should move
no bits. That is what `bench/xcheck_roshambo2.py` does and what
`tests/data/golden_scores.npz` was for. Nothing here replaces it.

### The line, stated once, because this section got it wrong three times

Drafting section 4 produced three separate attempts to pin something — the
vector width, then `exp2`, then FMA contraction — and the author pushed back on all
three. They were the same mistake, so it is worth naming the generator rather
than the instances.

**`doc/NUMERICS_POLICY.md` pins the arithmetic *within one implementation*, so
that two runs of the CUDA kernel are comparable with each other. This decision
governs comparison *across* implementations, where the policy's own D001/T25
already concluded the opposite: compare rankings, not bits.** Applying
within-implementation pinning to a cross-implementation comparator is the error,
and it is seductive because the pinning rules are the more familiar half of the
policy.

The practical test, and T24 already did the measuring. Its six axes all land on
the **same** saturated output distribution — that is its headline finding, and
the reason the policy pins rather than tolerances. Two of them:

| axis | median | p99 | max | basin flips |
|---|---:|---:|---:|---:|
| `-fmad=false` (FMA contraction) | 6.0e-8 | 2.7e-5 | 2.1e-2 | 1.24% |
| reordered reduction (**= vector width**) | 8.9e-8 | 2.8e-5 | 1.7e-2 | 1.20% |

FMA contraction is **not** more invasive than vector width; it is the same
distribution. Accepting one and pinning the other was incoherent on the
project's own numbers. And a change of `exp2` implementation is larger than
either.

**So: an axis on T24's saturated list is recorded in the stamp and judged on
recall. It does not additionally get pinned in a cross-implementation
comparator.** Contraction is determined by the compiler, its version and its
flags, all three of which T118 already requires in every CPU record — exactly
as libm is. There is nothing left for a separate pin to add.

**What is still off, and it is a different thing -- but DEFERRED, not ruled
out:** `-ffast-math`, `-funsafe-math-optimizations`, `-Ofast`,
`-fassociative-math`, `-ffinite-math-only`. These are not one-ULP effects. They
license transformations of unbounded size -- reassociation the source never
asked for, assuming no NaN or Inf, flushing denormals -- so unlike the axes
above they sit *outside* T24's measured envelope and cannot inherit its
conclusion. `numerics.SUSPECT_CXX_FLAGS` lists them for that reason, and T119's
build sets `-fno-fast-math -fno-associative-math`.

**That is the current setting, not a standing refusal.** On a CPU these are a
real throughput knob and the eventual answer may well be to turn some of them
on -- the same shape of question as the `exp2` grade, judged the same way, on
recall against throughput. What they are not is something to reach for before
the ladder has established what the kernel costs without them, since an
unbounded numerics change folded in early contaminates every arm measured
after it. **T121 carries it as a deferred arm** and owns naming the
measurement; the flags stay off until it does.

**T129 owns building it.** Until it exists, comparisons run as section 3
describes and the gap is recorded rather than papered over.

## What is measured, and what is assumed

Measured (T119, `results/T119/`): the oracle agreement above; retrieval against
the GPU FIELD path on a common subset of an internal evaluation corpus at 8 queries x 2,048
library conformers — **recall@100 mean 0.9925 / min 0.98 / p10 0.987**,
**RBO_ext(p=0.98) mean 0.9907 / min 0.975**, **top-1 agreement 8/8**.

Assumed, and owed: that the width-dependence is *as small as* the
architecture-dependence D001 measured. Nobody has taken it, because there is no
vectorized arm yet. **T122 owes it**: the first thing a second width produces
must be the ranked-output comparison against the scalar arm, before any
throughput number from it is quoted.

### T182 compact-source pose-transform declaration (2026-10-06)

T182 grains 16/17 assign four independent starts of each of two pairs to the
eight YMM lanes. Grain 16 reuses the T180 evaluator and transform. Grain 17
forms the compact `[A,A,A,A,B,B,B,B]` source vector with two XMM broadcasts and
an XMM-half insert, then applies each lane's pose with an AVX2 double-precision
FMA transform before the existing fp32 pose pack and T180 color polynomial.
That compact transform may round differently from T180's scalar double
coordinate expression; it is a declared transform/contraction change, not a
new Gaussian, cutoff, fallback, matrix guard, or within-start reduction.

Consequently, grain 17 is checked against the independent fixed-pose reference
with the declared fixed-pose tolerance, compared on exact own-pose ranked
output and same-backend optimizer ranks, and must continue to use exact scalar
per-start and winner scoring. Bitwise optimizer-trajectory identity is not a
gate. Grain 16 introduces no transform or arithmetic change beyond scheduling
the same four starts in independent lanes. Neither grain changes the CPU
default or the Tier 3 specification.

### T191 shared FP32 reduced-pose declaration (2026-10-07)

The ordinary CPU combo contract `shared_fp32_reduced_v1` changes pose and
color-coordinate arithmetic while retaining the same physical overlap
function. After composing the selected start with the optimizer state, the
implementation normalizes the composed quaternion once in FP32 and builds
one FP32 transform `M = COORD_SCALE * R` and reduced translation
`t' = COORD_SCALE * t`. Shape, analytic color, scalar fallback, each exact
per-start score, and the distinct final-winner score consume those exact
prepared bytes. The production exact scorer may accumulate in FP64, but it
must not renormalize the quaternion or rebuild a separate pose.

Query color features are owned once in the reduced frame, `A' = s*A`; library
color features remain physical and are transformed as `M*B + t'`. Signed
Gaussian decay is prepared once as `d' = d/(s*s)` with the amplitude
coefficient unchanged. Translation descent is with respect to the optimizer's
reduced `t'` and has no second `1/s` conversion. Torque uses the same prepared
transform, reduced displacement, and existing sign/factor. FP32 pose,
query-coordinate, decay, and reduced-frame rounding can move values and
trajectories relative to the separately labelled legacy physical-space FP64
pose path; bitwise trajectory identity with that legacy path is not an
acceptance criterion. The independent physical-space high-precision reference
remains an oracle for the declared change, not a production fallback.

This declaration applies to the ordinary CPU combo dispatch for supported
shape, analytic-color, and reviewed color-field combinations. The shared
prepared pose is mandatory for these paths regardless of any throughput result;
it is not a speed toggle. The separately named
`legacy_physical_fp64_pose` remains an explicit comparator and does not silently
stand in for the shared contract. Within the shared path, same-source
plan/scratch ON/OFF ablations retain bitwise same-backend parity, while
cross-contract correctness and retrieval decisions follow D029's declared
tolerance and ranked-output rules. The contract does not change the Tier 3
specification.

### T194 CPU color grain build availability (2026-10-07)

The default CPU build retains scalar grain 0 and shared-pose analytic grains
11 and 16. Historical grains 1–10, 12–15, and 17 are compiled only when
`ROSHAMBO3_CPU_EXPERIMENTAL_COLOR_GRAINS=ON` is selected at build time. Their
IDs and semantics remain stable for historical reproduction. Requests for a
grain omitted from a build fail explicitly; extension metadata distinguishes
compile availability from target compilation and runtime ISA availability.
This selection does not alter mode-2/mode-3 defaults, start mappings, supported
retained field policies, shape backends, or GPU code. It is a bounded default
build-size/reachability decision, not a claim that the experimental grains can
never be useful. Optional invariant-plan and exact-final-scratch reuse remain
off by default.

## Reopening condition

A CPU arm whose ranked output differs from the scalar kernel's by more than
`doc/METRICS.md` §8's threshold — paired bootstrap over queries, BCa 95% CI
excluding 0 **and** a point estimate above delta = 0.01 — at any width. That
would mean the amplification is materially worse on a CPU than the 480/480 D001
measured across GPUs, and the acceptance in §3 would have to be re-argued
rather than inherited.
