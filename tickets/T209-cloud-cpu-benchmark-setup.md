---
id: T209
title: Stage and validate the dedicated cloud CPU benchmark host
phase: 2
lane: infra
status: closed
model: sol
reviewer: sol
depends_on: [T207]
priority: high
artifacts: results/T209/
---

## Scope

The author provisioned a dedicated cloud x86 VM and authorized copying code,
benchmark data and building. Initial AMD host: Ubuntu 24.04, Python 3.12, GCC 13.3, CMake 3.28;
24 AMD EPYC 9B45 cores/48 threads (larger than the 16-vCPU VMs used for the paper's portability table), AVX2/AVX512, one guest NUMA node.
Create isolated source, environment and dataset paths; no corpus rewrites,
kernel changes, default promotion, or timing campaign in this setup ticket.

Source: the development checkout. The VM's shared project root holds
`datasets/`, `envs/`, `runs/`, `locks/` and `staging/`. Initial transfer includes current main 254ac933 and complete
t169_pubchem (296477561 bytes); no need for the full dataset collection.
CPU-only Release build, CUDA OFF, experimental color grains OFF, default
x86-64-v3 arithmetic flags; two compiler jobs. Record dependency freeze,
source/native/DSO/corpus stamps and test logs before readiness.

## Setup findings

### Replacement Intel C4 host

The author recreated the cloud x86 VM as an Intel C4 instance after the original
AMD setup, which changed the guest hostname. Register that exact name
with the same canonical lock; keep unknown hosts fail-closed. Restore the
same directory layout, frozen panel and isolated environment from scratch.
Fresh source/native build revision: `ccc54ba9df0677d9ab8966389d3fe54e6f4d440f`.
The Intel Xeon Platinum 8581C exposes 24 physical cores/48 SMT threads;
sibling CPUs are `i` and `i+24`. PMU collection is now empirically working:
`perf stat` returns nonzero cycles, instructions, reference cycles,
branches, branch misses and `l2_rqsts.miss`. Keep default perf security
settings unchanged. The fresh CPU-only
Release build passed all 155 focused tests. Preserve Intel evidence separately
from the original AMD evidence below; neither setup run establishes throughput.
Full-corpus check completed with 393216 pair rows at each of 8 and 16 workers,
and zero actual native shape/color library-self evaluations. Fresh isolated
T149 ON/OFF builds passed all eight arms with no score movement. A checksum
dry-run (`rsync -rcni`) verified every transferred dataset file against the
local frozen panel with no differences. The initial transfer had a redundant
directory level; flattening it resolved a missing-manifest receipt failure
before any corpus scoring began. No data was rewritten or removed.

Intel evidence: `results/T209/<cloud-vm>_intel_20261009/raw/`, including PMU,
host inventory, dependency freeze, build receipt/log, tests, full check ledger
and canary. Native build and checked source are both `ccc54ba9`.
Original AMD evidence: `results/T209/<cloud-vm>_20261009/raw/`; its native build
was at `254ac933`, while final checks ran at `0c18b11c` with unchanged native,
CMake and pyproject inputs and the same installed DSO. Its isolated final
canary rebuilt `0c18b11c` separately. Preserve unsuccessful intermediate AMD
runs as failures, not acceptance evidence. The AMD VM no longer exists.
No further manual setup was required for the replacement.
Independent review approved source and complete archive at `206e7303`;
all 331 archived checksum entries verified. Setup is complete, not a timing
campaign or a promotion of an optimization default.

### Original AMD C4D host (retired)

Initial focused run: 150 passed/3 failed. Two tests assumed native return_dense
was the last positional parameter, predating time_library_self. One assumed
at least 3 workers claim 3 short tasks, which dynamic ownership does not guarantee.
Fix only test ABI indexing and the invalid occupancy assertion; retain exact
scores, IDs, all 20 columns, unique work count and failure-discard assertions.
Register the exact guest hostname's canonical CPU lock; unknown hosts still
fail closed, and no timing/window receipt is implicitly authorized.

Guest cpufreq sysfs unavailable; existing sampler falls back to /proc/cpuinfo,
whose VM-reported MHz is not proof of achieved physical frequency. Perf
cycles/instructions counters are unavailable on this guest; do not alter kernel
perf settings to try to create absent PMU counters. Google currently documents PMU enablement for
A4X/C4A/C4/M4, not C4D. Causal timing/phase attribution remains available.

## Acceptance

Full check at 7f completed both 393216-row score passes with self 0/0 but failed
while writing its ledger: GPU metadata unconditionally invoked nvidia-smi on
this CPU-only VM. Handle missing executable explicitly as unknown GPU metadata
with telemetry_error, preserving available-GPU behavior and all grade gates.
Add missing/present utility regressions. Preserve the failed run; repeat full
correctness with the ledger fix rather than treating partial scoring as a
completed run. No NVIDIA installation or dummy utility is warranted.

Transferred manifest matches; clean source and private installed DSO agree;
focused worker-owned/conformer+molecule/codec tests pass after scoped test
maintenance; full real-corpus correctness-only check and fresh T149 canary.
Independent review for test/runner changes. No cloud rates claimed here.
Preserve baseline failed test log and all build/correctness receipts. No GitHub
pushes or shared-environment modifications.
