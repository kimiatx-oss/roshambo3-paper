# D023 — Two measurement regimes: calibration, and headline

**Date:** 2026-08-21
**Status:** active
**Source:** `decisions/D004`, `D006`, `D007`
**Constrains:** every timed run from here on, and which machine may produce which
number
**Supersedes:** the operative reading of D006's blanket prohibition on tachi
throughput numbers, and the implicit assumption in D004/D007 that a locked clock
is always the right one

## The problem this fixes

D007 established a rule that is correct and stays: **numbers taken at different
clocks are different measurements and must never be combined into one ratio,
table, or derived quantity.** From that, the project drifted into a second
assumption that was never argued: that a *locked* clock is what every run wants.

It is not. Locking a clock deliberately gives up performance to buy consistency.
That is exactly right when the question is "which of these two implementations is
faster", because the answer must not depend on thermal state. It is exactly wrong
when the question is "how fast is this tool", because nobody deploys a card
pinned below its own boost range, and a number taken that way understates what a
reader would reproduce.

D006 has the mirrored problem. It says flatly:

> Absolute throughput. ... Nothing quoted as pairs/s or a projection to 1e9/1e11
> may come from tachi.

That was written for **calibration** — choosing an optimization path on the basis
of measured throughput, where a slower card with unlockable clocks and no `ncu`
would mislead. It was not written about a *comparison between two tools on one
card*, which is a different claim with different failure modes, and which is the
one measurement that can answer "is the speedup an artifact of newer hardware".

## The two regimes

**Calibration.** Clocks locked; one clock region for every arm; used to decide
between implementations, to attribute a bottleneck, or to bank a lever. D006's
prohibition applies here without change: no absolute pairs/s and no 1e9/1e11
projection from tachi, and occupancy or register-pressure conclusions come from
Blackwell.

**Headline.** Clocks **unlocked**, because the card's natural operating point is
the one a reader gets. Record the achieved clock distribution, the
`sw_power_cap`-active fraction, and whether a profiler held clock control —
report the distribution, assert nothing. On roci this means `nvidia-smi -rgc`
before the run; D007's machine-of-record section currently describes roci as
locked to 1402/1395 MHz, which is the calibration state, not this one.

**D007's rule is untouched and binds harder.** A calibration number and a
headline number are numbers from different clocks. They may not be combined into
one ratio, and neither may be quoted as the other. Every run record carries a
`measurement_regime` field so the two cannot be mixed by accident rather than by
decision.

## tachi's standing, restated

tachi may produce a **quotable comparison ratio**: two or more arms, on one card,
in one clock region, in one session. That is what licenses the
matched-architecture head-to-head against the published ROSHAMBO2 numbers — its
TITAN V is the same GPU model that paper benchmarked, which removes the hardware
objection from the speed claim rather than arguing around it.

tachi still may not produce a quotable **absolute** pairs/s, and nothing on tachi
may ground a projection to 1e9 or 1e11.

Two tachi constraints are unchanged and must be recorded on every run there:
clocks cannot be locked, so the achieved distribution is
all there is; and `ncu` counters are unavailable, so D009's causal-ablation
method is the only attribution available.

## Reopening condition

If a headline run's achieved clock distribution is wide enough that two arms in
the same session cannot be compared — a throttle fraction materially different
between arms — then the headline regime has failed on that machine and the run
reverts to calibration with the cost stated. Measure it; do not assume it either
way.

## Amendment (the author, 2026-10-22): absolute headline rates from tachi

tachi **may** produce quotable **absolute headline** rates (pairs/s), taken in the
headline regime above: clocks unlocked, the achieved clock distribution and
`sw_power_cap` fraction recorded with the run, and the run otherwise held to the
GPU-lock and idle-host rules. The restriction stays for **calibration**: no
optimization, bottleneck or lever decision rests on a tachi rate, and nothing on
tachi grounds a projection to 1e9 or 1e11. Reason: the paper's TITAN V numbers are
what a reader with that card gets; the old prohibition was written for choosing
implementations, not for reporting one.

Cross-session ratios (also the author, 2026-10-22, for T300): the TITAN V head-to-head
against ROSHAMBO2 (T114) is recomputed as the archived ROSHAMBO2 rates over the new
format-3 ROSHAMBO3 rates. Those arms come from different sessions, so the ratio is
**not** a same-session comparison in the sense above; the paper must say which
session each side comes from, and the reopening condition (clock distributions
compared, not assumed) applies to the two records.
