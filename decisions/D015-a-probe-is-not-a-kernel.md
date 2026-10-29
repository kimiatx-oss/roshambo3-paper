# D015 — A probe is not a kernel: validate the harness before trusting its ranking

**Date:** 2026-08-17 (strengthened 2026-08-17 by T30, which the rule caught something with — but
not the thing it was looking for)
**Status:** active, permanent
**Raised by:** the author, on the Volta texture result

## The rule

**Before a ranking measured in a purpose-built probe is believed, show that the probe tracks the
production kernel — on every machine the ranking is claimed for.**

Report the probe/production ratio explicitly. If that ratio differs between machines, the probe
cannot rank anything across them, because the distortion is not common-mode.

### The rule's second half, added by T30

**A cost ratio is necessary and not sufficient. The probe must also match production in the SHAPE
of the work — the loop bounds, the branches, the trip counts — not only in its cost per unit of
work.**

T30 measured the ratio this rule asks for and `t28_probe.cu` **passed**: production/probe on the
shared analytic arm is **1.73× on Volta against 1.81× on Blackwell** at the panel-mean query size,
common-mode to 4%, and indistinguishable at larger queries. Had that been the whole test, D014
would have been confirmed and the ranking would still have been wrong.

What actually broke the ranking was a difference the ratio cannot see. The probe's atom loop runs
`j < L` with a `w == 0` skip over the padding; production's runs `j < nreal[conf]`. Both do
identical work — T30 verified the outputs are **bit-identical over 446,800 conformers** — but the
padding branch fragments the texture arm's unrolled body into five separately-reconverged regions
and costs it **1.41–1.73× on Volta against 1.06–1.15× on Blackwell**. **That differential, and not
any per-pair cost, is what inverted the ranking between the architectures.**

> A probe that is uniformly 1.8× leaner than production can still rank two arms backwards, because
> leanness is common-mode and *shape* is not. **State the probe's loop bounds against production's
> before quoting a probe-derived ranking, and prefer to make them the same.**

## Why this is now a standing rule

This is the **fourth** instance of one failure in this project, each in a different disguise:

1. **T10** priced "scattered `molB`" at 1.04× by ablating on an *idealised* loop; the real figure
   is 1.16×, because L1TEX has nothing else to do in the idealised one.
2. **T14** projected the transposed tile at 1.22× from a fit treating instructions and sectors as
   **independent additive** costs; measured 1.10×, with a 15% cross-term.
3. **T27** built its whole ticket on "the target is re-read from global on all 100 steps",
   inferred from source; SASS showed **zero `LDG`** — the compiler already hoists it.
4. **T28/T29** ranked `half4` texture against the software brick, and inverted that ranking
   across architectures, entirely inside `t28_probe.cu` — a harness T28 itself documents as
   **"roughly twice as lean per pair term"** as production, and which was **never built as the
   production kernel on Volta at all**. **T30 confirmed the leanness (1.73×/1.81×, common-mode)
   and found the inversion anyway, in the probe's loop shape.** The leanness was innocent; the
   instinct to distrust the probe was not.

## The specific hole in the texture result — as it was written, before T30 closed it

T29's Volta numbers are internally consistent and carefully controlled — matched conformers per
SM, an fp32-texel control anchoring both machines to 2%, replication to 0.03–0.14%. **None of that
addresses whether the probe distorts the two architectures equally.**

Two attempted mechanisms have already failed to explain the inversion:

- *"The TMU is idle, so offload to it"* — refuted by T28: texture pipe utilisation never exceeds
  4.1%, and 24 hybrid cells all lose.
- *"Volta's fp16 texture path is saturated"* — refuted by the data itself: a saturated path would
  be flat in `h`, and Volta's `tex4h` runs 0.427 → 0.323 samples/SM/clk from h = 1.2 to 0.5.
  Meanwhile removing the bounds test buys **exactly nothing at every resolution** (0.4272 vs
  0.4268, 0.3940 vs 0.3949, …), which is not what a path with headroom does.

When two plausible mechanisms both fail and the numbers still look odd, **the harness is the
next suspect, not the third mechanism.**

## What to do

- State the probe/production ratio, per machine, before quoting a probe-derived ranking.
- **State the probe's loop shape against production's**, and make them the same where the feature
  under test is not what differs. T30's ablation is the pattern: put the shape difference behind a
  template parameter and run both arms in one process on one card, then check the outputs are
  bit-identical so the comparison is not a speed/accuracy trade in disguise.
- **Report registers and blocks/SM per cell.** Removing (or adding) a branch changes what `ptxas`
  will pipeline: T30 found `tex4`/`tex4h` moving to 73 registers on sm_70 and 80 on sm_120 at the
  production loop bound while the other arms stayed at 64, an occupancy difference *inside* the
  comparison. Run the sweep twice — as-is and with `__launch_bounds__` pinning every arm — and only
  take a conclusion where the two agree.
- Where the production kernel lacks the feature under test (as with the grid today), validate on
  the arm they **do** share — here, the analytic arm — and report whether the probe's leanness is
  the same on both machines.
- Prefer landing the feature in the production kernel and re-measuring there. A ranking that
  survives that is worth more than one defended by controls inside the harness.
