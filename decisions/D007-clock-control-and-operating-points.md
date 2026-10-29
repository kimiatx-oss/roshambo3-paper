# D007 — Clock control: profilers seize the clock, and numbers from different clocks must not be mixed

**Date:** 2026-08-16
**Status:** active, permanent
**Applies to:** every ticket that profiles or times anything

## The mechanism, so nobody re-diagnoses it

**Nsight Compute takes control of the GPU clock while profiling.** `ncu --clock-control` defaults
to `base`, so for the duration of a profiling run it overrides any external
`nvidia-smi -lgc` lock and restores the previous setting on exit. `nsys` can do likewise.

This was diagnosed the hard way: the author set `-lgc 1402,1402`, saw 1740–1792 MHz in
`nvidia-smi dmon`, and reasonably concluded the lock had failed. It had not — a sibling ticket's
`ncu` run was profiling at the time. Sampling during that run showed the clock pinned at exactly
**2265 MHz across six consecutive samples**, which is a lock, just not the one the author set.

Symptoms that look like a broken lock but are not:
- observed clock **above** the locked value
- observed clock rock-steady at a value nobody configured
- clock changing when a profiling job starts or ends
- `Applications Clocks Setting: Not Active` in `nvidia-smi -q` while a lock is set

Check `ps aux | grep -E "[n]cu|[n]sys"` before concluding anything about clock state.

## The rule

**Numbers taken at different clocks are different measurements and must never be combined into
one ratio, table, or derived quantity.**

Specifically forbidden:
- a counter from an `ncu` run divided by a wall-time from a locked-clock run
- "% of peak" where the peak was computed at a different clock than the measurement
- a before/after speedup where one side ran under a profiler and the other did not
- any dispersion or confidence interval pooled across operating points

Specifically fine:
- counters compared **among themselves** from `ncu` runs — that is precisely what ncu's clock
  control is for, and it makes them internally comparable
- timings compared among themselves from locked-clock runs

## Requirements on every run

1. **Record the achieved clock distribution**, not the requested one. `clocks.sm` sampled through
   the run, plus `clocks_event_reasons.active`. "Clocks locked" is not a sufficient claim: this
   card spends much of its life power-limited (SW power-capping counter ~2167 s accumulated;
   T04 measured 249.5 W mean / 291.1 W peak against a 300 W cap), and a run whose
   `sw_power_cap` was Active for a meaningful fraction was **power-limited, not clock-locked**.
2. **Record whether the run was under profiler clock control**, and which tool.
3. **State which clock any "% of peak" figure was normalised against.** The project has been
   quoting "5.6% of the MUFU.EX2 ceiling" without saying whether that ceiling was computed at
   1402, 2265, or the 3090 MHz nameplate — the same measurement yields three different answers.

## Worth measuring once, then reusing

Run the counters once with `--clock-control=none` (respecting the external lock, at the cost of
noisier counters) and check whether the **ranking** of stall reasons is stable between that and
ncu's default clock. If what bottlenecks the kernel changes with clock, that is a finding in its
own right for T13/T14/T15 and changes how much any single-operating-point profile is worth.

## Enforcement

Documentation does not hold — this project's repeated lesson. **T26** adds the check to
`tools/roshambo3_bench`: stamp the achieved clock and profiler-control state into every run
record, and refuse or flag a comparison whose two sides carry different operating points.

## Machine state of record (roci)

Locked to **1402 requested / 1395 observed**, persistence on, `sw_power_cap` inactive at that
frequency — chosen because it sits below the point where the power ceiling starts making the
decisions. Earlier attempts at 1800 did not bind: the card sat at 1762 with `sw_power_cap`
Active. See `decisions/D004`.
