# D011 — How to wait for a long-running job

**Date:** 2026-08-16
**Status:** active, permanent
**Applies to:** every ticket that runs a job longer than a single tool call

## The failure this prevents

Four agents have now lost large fractions of their budget waiting badly, in two distinct ways:

1. **Stop-and-resume around a background monitor.** T01, T04 and T09 each halted repeatedly
   waiting on a `Monitor`, and every halt costs a full resume with the whole context re-read.
2. **Waiter proliferation.** T13 accumulated **15 concurrent waiter shells** polling for one
   output file, at 60/90/120 s intervals plus blind `sleep 900/1200/1500/1800/3000`. Its actual
   run was healthy the whole time and had been producing usable results for a long while.

In T13's case the run had completed five of nine work units and its headline number was already
visible in the log. None of the fifteen waiters were reading it.

## The rules

**1. Wait on the progress signal, not the terminal artefact.** If a job writes incremental
output — a log line per work unit, a partial result file — poll *that*. Waiting for the final
file discards every intermediate result and turns a partially-answered question into a blocked
one.

**2. Never issue a blind `sleep N`.** It cannot detect early completion and it cannot detect
failure. A 50-minute blind wait returns nothing useful if the job died in minute two. Always
bound a wait by a *condition*, with an iteration cap:

```bash
for i in $(seq 1 20); do
  n=$(grep -c '^{' run.log); [ "$n" -ge 9 ] && break
  sleep 60
done; tail -5 run.log
```

**3. One waiter at a time.** Overlapping waiters do not make work finish sooner; each is a
blocked tool call and every duplicate is pure loss.

**4. Prefer doing analysis to waiting.** Partial results are results. Write the analysis, the
report skeleton, and the verification against the units that have landed, then fold in the rest.
This converts dead waiting time into finished work.

**5. Short jobs run in the foreground.** Anything under ~10 minutes fits a single `Bash` call
with a generous `timeout`; that is strictly better than backgrounding it and polling.

**6. Commit before you wait.** Three agents were killed mid-run by API spend-limit errors and two
lost everything because nothing was committed. A partial commit with an honest message is
recoverable; an uncommitted worktree is not.

## Diagnosing from outside

If a ticket seems stalled, check whether the *work* is alive before assuming the agent is stuck:

```bash
nvidia-smi --query-gpu=utilization.gpu,power.draw --format=csv,noheader
ps aux | grep "[r]un_all"                 # or the job's own name
ls -la <worktree>/results/T<NN>/          # what has actually landed
git -C <worktree> rev-list --count <integration-branch>..HEAD   # is the work committed
```

A healthy run with a stuck waiter is a protocol problem, not a compute problem, and the fix is to
read the log rather than to restart anything.

---

## AMENDMENT (T37, 2026-08-19) — the GPU gate must be bounded, or two tickets deadlock

**T36 and T37 deadlocked twice and lost two runs.** The cycle:

* T36's `tickets/T20/run_pipeline.py` keeps a **CUDA context alive** (550 MB resident, 0% util)
  while it blocks waiting for the GPU flock.
* T35's inherited `wait_for_clean_card()` **holds that flock** and spins until the card reports
  empty — which it never will, because the thing keeping it non-empty is blocked on the flock.

Neither agent was misbehaving; the protocol was. **A blocking wait that holds a lock while waiting
for a condition another lock-waiter must clear is a deadlock by construction.**

Required of every ticket runner from now on:

1. **The clean-card gate is bounded.** T37's fix: `--card-wait-s` (default 1800, `0` for correctness
   runs) and a recorded `card_wait_timed_out` flag. Propagate it — do not write a new unbounded
   `while not card_empty: sleep`.
2. **Do not hold a CUDA context while blocking on the GPU lock.** Acquire the lock first, then
   initialise the context.
3. A run that proceeded after a gate timeout is **advisory**, and the run record must say so.
