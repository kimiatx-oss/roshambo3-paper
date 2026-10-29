# RTX PRO 6000 roofline ladder at 3bb39f69 (2026-10-23)

References to `results/`, `tickets/`, `doc/`, `hosts/` and other files not in this repository point at the internal development record.

> **Paper import.** Only `ladder-summary.json` and this README are archived here; the L4 ladder is in `../roofline-ladder-l4-3bb39f69/`. `d5-pair-weights.json`, `roofline-ladder.tsv`, `run.log`, the raw ncu reports and the host scripts this README cites stay in the internal record. The source corpora are internal: their names are replaced by generic labels (`internal tuning corpus`, `internal scale corpus`, `[private corpus]`) and their `corpus.json` sha256s are `[withheld]`.

These are Nsight Compute profiles of `optimize_pairs_field_kernel` and `optimize_pairs_analytic_kernel` on roci at the frozen benchmark commit 3bb39f69. roci has an RTX PRO 6000 Blackwell Max-Q (GB202, sm_120, 188 SMs, 300 W cap). The ladder has the same 16 points and method as the L4 ladder in `../roofline-ladder-l4-3bb39f69/`: one launch per D5 launch-width class, weighted by D5's pair evaluations. That README has the method, the weights and the class assignment, all unchanged here.

## How it ran

- The command was `bash hosts/run-roofline-profile.sh roci ladder`, after a `ladder-plan` check (96 ncu commands, 16 points × 2 arms × 3 passes).
- It ran from 12:19:34 to 12:27:41Z.
- It held the per-device GPU lock and the default-base lock for the whole run.
- Preflight found the card idle: no compute process, no ncu, nsys or MPS. All 96 pre-pass snapshots in `run.log` show no foreign compute process.
- The ncu version was 2026.1.1, with driver 595.91.07. ncu ran as the benchmark user.
- Each source `corpus.json` sha256 matched the spec. `launch-shape.json` matches the spec at every point, and `ladder-summary.json` → `problems` is `[]`.
- Profiled SM clocks were 1006 to 1032 MHz under `--clock-control base`. These are attribution numbers. **Never combine them with benchmark wall times.**

**The summary step was rerun by hand.** The profiling finished, but `roofline_ladder_summary.py` crashed reading `clocks-<arm>.csv`. ncu 2026.1.1 on roci prints thousands separators in `--page raw --csv` (`"4,092"` for the grid size), and the L4 host's ncu does not. The fix strips the commas in the clocks parser, the same way `roofline_summary.py` already treats metric values. The rerun then wrote `ladder-summary.json`, and the checksums and the final `run.log` lines were added by hand. Nothing was re-profiled. Regenerating the committed L4 `ladder-summary.json` with the patched script is byte-identical.

## Per-point results (RTX PRO 6000; L4 in brackets)

The columns are:
- **iss %:** `smsp__issue_active`.
- **FP32 %:** (fadd + fmul + 2·ffma) / (time × SMs × 128 × 2 × clock).
- **warps %:** `smsp__warps_active`.
- **xu %:** the XU pipe.
- **winst/pair:** warp instructions per pair evaluation.

| point | class (b, L, Lf) | n_real | field iss % | field FP32 % | field warps % | field winst/pair | analytic iss % | analytic FP32 % | analytic xu % | analytic warps % |
|---|---|---|---|---|---|---|---|---|---|---|
| p00 | 0,16,16 | 10 | 86.6 [82.0] | 25.8 [27.4] | 62.5 [65.0] | 7345 [6294] | 72.2 [70.0] | 30.5 [31.8] | 78.3 | 30.4 [32.4] |
| p01 | 1,16,16 | 12 | 85.2 [80.4] | 30.6 [29.2] | 62.5 [64.9] | 6863 [6280] | 72.3 [70.0] | 30.7 [31.9] | 78.7 | 30.4 [32.4] |
| p02 | 1,16,16 | 14 | 84.0 [81.2] | 20.8 [25.7] | 62.5 [64.9] | 10254 [7748] | 72.4 [70.1] | 30.7 [31.9] | 78.9 | 30.4 [32.4] |
| p03 | 2,16,24 | 16 | 69.6 [77.7] | 25.3 [29.2] | 61.2 [64.5] | 7115 [6998] | 72.4 [70.0] | 30.8 [31.9] | 79.0 | 30.4 [32.4] |
| p04 | 2,24,24 | 18 | 60.4 [66.4] | 20.5 [23.9] | 46.7 [48.7] | 8476 [7787] | 72.4 [70.1] | 30.8 [31.9] | 79.1 | 30.4 [32.4] |
| p05 | 3,24,24 | 21 | 57.5 [63.3] | 18.0 [21.1] | 47.5 [48.7] | 10356 [9237] | 72.5 [70.1] | 30.8 [32.0] | 79.2 | 30.4 [32.4] |
| p06 | 4,24,32 | 24 | 58.8 [51.3] | 22.7 [20.2] | 32.0 [32.5] | 9185 [8496] | 72.4 [70.0] | 30.8 [31.9] | 79.2 | 30.4 [32.4] |
| p07 | 4,32,32 | 26 | 56.6 [48.6] | 19.9 [18.4] | 32.2 [32.6] | 10884 [9283] | 72.4 [70.0] | 30.8 [32.0] | 79.3 | 30.4 [32.4] |
| p08 | 5,32,32 | 29 | 51.7 [46.8] | 16.0 [16.5] | 32.3 [32.8] | 13209 [10735] | 72.4 [70.0] | 30.8 [32.0] | 79.3 | 30.4 [32.4] |
| p09 | 6,32,40 | 32 | 52.6 [48.3] | 20.9 [19.6] | 31.9 [32.5] | 10031 [9986] | 72.4 [69.9] | 30.8 [32.0] | 79.3 | 30.4 [32.4] |
| p10 | 6,40,40 | 35 | 49.7 [46.2] | 19.4 [18.5] | 32.3 [32.8] | 11392 [10775] | 65.2 [60.8] | 27.7 [27.8] | 71.5 | 16.7 [16.7] |
| p11 | 7,40,48 | 39 | 31.5 [25.8] | 11.3 [9.7] | 16.5 [16.5] | 13273 [12226] | 65.3 [61.0] | 27.8 [27.9] | 71.6 | 16.7 [16.7] |
| p12 | 7,48,48 | 42 | 29.4 [25.0] | 11.0 [10.0] | 16.5 [16.6] | 13801 [12272] | 65.3 [61.0] | 27.7 [27.9] | 71.6 | 16.7 [16.7] |
| p13 | 8,48,56 | 45 | 27.8 [24.6] | 9.4 [9.3] | 16.5 [16.6] | 16126 [13724] | 65.4 [61.1] | 27.7 [28.0] | 71.8 | 16.7 [16.7] |
| p14 | 8,56,56 | 48 | 25.4 [24.1] | 10.5 [10.1] | 16.6 [16.6] | 12948 [12975] | 65.4 [61.1] | 27.8 [28.0] | 71.8 | 16.7 [16.7] |
| p15 | 9,56,56 | 50 | 25.3 [23.9] | 10.0 [9.8] | 16.5 [16.6] | 14308 [13764] | 65.4 [61.2] | 27.8 [28.0] | 71.8 | 16.7 [16.7] |

**Registers are constant across all 16 points:** 64 per thread for field and 111 for analytic. On L4 they are 64 and 118. The analytic count differs between sm_120 and sm_89, but within each device it does not vary.

## D5-weighted aggregates (`ladder-summary.json` → `work_weighted`)

| | field, RTX PRO 6000 | field, L4 | analytic, RTX PRO 6000 | analytic, L4 |
|---|---|---|---|---|
| warp instructions per pair | 10685 | 9381 | 71167 | 68526 |
| FP32 FLOP per pair | 2.35e5 | 2.20e5 | 2.15e6 | 2.06e6 |
| XU warp instructions per pair | 451 | 445 | 9734 | 9734 |
| issue active % | 53.3 | 50.4 | 70.6 | 67.7 |
| issue % from counts | 52.1 | 50.0 | 63.5 | 65.8 |
| FP32 % of peak | 17.9 | 18.3 | 30.0 | 30.9 |
| FMA pipe % | 34.8 | 32.5 | 51.6 | 47.2 |
| XU pipe % | 17.9 | 19.1 | 77.3 | 76.9 |
| L1TEX % | 48.5 | 63.8 | 16.7 | 16.9 |
| warps active % | 36.5 | 36.2 | 26.9 | 28.4 |

The two devices reach the same conclusions:
- The field kernel is occupancy- and latency-limited across D5, at about 50 % issue. The 12-atom launch, at 85 % issue, is its best case.
- The analytic kernel is XU-bound throughout, at about 77 % XU. Warps active halve at L ≥ 40.
- Occupancy steps are identical: field warps active go 62 % → 47 % → 32 % → 16.5 % at L_field_width 16, 24, 32 to 40 and ≥ 48.

## Surprising

> **Resolved after this README was written.** The sm_120/sm_89 field gap below is
> compiler code generation, not optimizer work: the step count is fixed. Four
> lanes share a pair and stride the atom loop by 4, so when the atom count is not
> a multiple of 4 their trip counts differ by one. nvcc 13.2 for sm_120 unrolls
> the loop 4x with 2- and 1-body tails that run serially at half-warp occupancy;
> nvcc 12.9 for sm_89 peels one iteration and unrolls 2x. A closed-form model of
> that codegen reproduces every texture-request count on both devices (32 of 32).
> Instantiation, grid and registers are identical, no data-dependent branch is
> involved, and numerics are unaffected. The speculation in this section about
> divergent optimizer steps or convergence checks is superseded. Per-device
> roofline conclusions are unchanged.

**The field kernel does more work per pair on sm_120 than on sm_89 for the same launch, and the excess is uneven across points.** Each launch is identical on both devices (same corpus file, group, launch index and rows).
- At most points the field instructions per pair are −0.2 to +17 % off L4's.
- At p02, p08 and p13 they are 32 %, 23 % and 18 % higher. At those three points the texture requests per pair are higher by exactly 208 (728 against 520, 1144 against 936, 1560 against 1352), and the threads per warp instruction fall (p02: 21.1 against 26.7).
- At every other point the texture requests per pair are equal on both devices.
- This looks like extra, divergent optimizer work in some rows, for example a different number of field steps taken. It is not register pressure (64 on both) and not a launch-shape mismatch (`problems: []`).
- The XU instructions per pair agree to within 1.4 %, and the analytic arm's are identical (9734). That points at the field path specifically.

This was not investigated further. The counts are deterministic from run to run: the 12-atom single profile at 12:34Z (not archived here) reproduces p01's warp-instruction, FFMA and texture counts exactly. So the excess is a property of the sm_120 build on these inputs, not noise. Possible causes are a different floating-point path through the optimizer's convergence checks, or a different code shape. One of those points would need a source-level look before a paper sentence relies on cross-device per-pair counts.

The p02 anomaly matters for the weighted aggregate. p02 carries about 96 % of the (1,16,16) class weight (6.4 % of D5), so roci's field per-pair instruction aggregate is about 14 % above L4's.

## Files

The layout is the same as the L4 ladder. Only `ladder-summary.json` is in this repository; `<point>/` (the zstd-compressed `<arm>.ncu-rep` files and their `SHA256SUMS`), `roofline-ladder.tsv`, `d5-pair-weights.json` and `run.log` are in the internal development record.
