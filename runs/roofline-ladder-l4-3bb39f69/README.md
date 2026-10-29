# L4 roofline ladder at 3bb39f69 (2026-10-23)

References to `results/`, `tickets/`, `doc/`, `hosts/` and other files not in this repository point at the internal development record.

> **Paper import.** Only `ladder-summary.json` and this README are archived here, redacted; `d5-pair-weights.json`, `roofline-ladder.tsv`, the raw ncu reports, `run.log`, the single 12-atom profile and the host scripts it cites stay in the internal record. The source corpora are internal: their names are replaced by generic labels (`internal tuning corpus`, `internal scale corpus`, `[private corpus]`) and their `corpus.json` sha256s are `[withheld]`. The paper uses this ladder's D5-weighted per-pair demand for the GV100 projection: NVVM gives sm_70 and sm_89 the same field atom-loop shape (one peeled iteration, then 2x unrolled), while sm_120 unrolls 4x with 2- and 1-body tails. The DRAM counter is unavailable on AD104, so that roof is omitted.

These are Nsight Compute profiles of `optimize_pairs_field_kernel` and `optimize_pairs_analytic_kernel` on the L4 host (NVIDIA L4, AD104, sm_89, 58 SMs) at the frozen benchmark commit 3bb39f69. There is one launch per D5 launch-width class, and the classes are weighted by D5's pair evaluations.

This ladder was run because the single profile in `../roofline-profile-l4-20261023T014308Z` is a 12-atom launch, while D5 averages 24.85 real atoms per conformer.

## Method

**Per point: the August method, unchanged except for `--launch-skip`.**
- Three ncu passes per arm, each with `--target-processes all --clock-control base --replay-mode kernel --kernel-name <kernel> --launch-skip <k> --launch-count 1`:
  - the 30 August metrics, as `--csv`;
  - the five August sections, as `--export`;
  - the DRAM read counter under AD104's own name, `dram__bytes_read.sum`. AD104 reports `dram__bytes_op_read` as n/a.
- The target is the frozen `publication/scripts/profile_roofline.py`: the first 4 PANEL-8 queries (PubChem3D), 25 steps, color off, and the screen restricted to one group.
- The script is `../../hosts/run-roofline-profile.sh l4 ladder`.
- The spec is `roofline-ladder.tsv`, which `hosts/roofline_launch_shape.py select` produced.

**Launch-width classes.**
- A launch's kernel arguments depend on the group's padded width `L` (stage width) and `L_field_width` (field spacing, min blocks per SM). See `ScreenConfig.for_width`.
- Format 3 sorts each bucket by real-atom count and splits it into groups of 2M conformers. In a large corpus, the first groups of a bucket can therefore be narrower than the bucket: D5 runs its 16-atom conformers at L=16 with L_field_width=24.
- D5 has 15 (bucket, L, L_field_width) classes. Each class gets one point: a full launch (about 65,536 rows, × 4 queries ≈ 262,144 pair rows) whose rows all have one real-atom count, at the count nearest the class mean.
- The 12-atom August point is kept for continuity (p01). Class (1,16,16) uses p01 and p02, interpolated to its mean of 13.92.

**Where the points come from.**
- The internal tuning corpus has every class whose `L_field_width` equals `L`.
- The internal scale corpus supplies the narrow classes, and the 10-, 42-, 48- and 50-atom launches that the tuning corpus cannot fill with a single atom count.
- [private corpus] supplies (8,48,56).
- Only the launch shape matters to the kernel, not which corpus it came from. Each source's `corpus.json` sha256 is checked against the spec.

**Checks that the right launch was profiled.**
- `launch-shape.json` matches the spec at every point (`problems: []`).
- Each profiled grid size matches its launch's row count, for example 4072 blocks for p13's 65,119 rows.
- R3gSource's Prefetcher yields jobs in order, so launch k of a one-group screen is job k.

**Weights** (`d5-pair-weights.json`, from `hosts/roofline_d5_weights.py`).
- w = the class's conformers / D5's conformers. That equals the fraction of pair evaluations, because every query meets every conformer.
- Class sizes come from D5's format-3 `corpus.json`. The per-class real-atom histograms come from walking `build.json` `statistics.hac_hist` through each bucket's groups in order. All 262 groups pass the check `L == pad8(max assigned n_real)`.
- The weights are not cost-weighted. `ladder-summary.json` carries the raw per-point counts, so a generator can apply its own per-pair cost.

**Work-weighted aggregates** (`ladder-summary.json` → `work_weighted`). These are T300's own numbers:
- per-pair demand: Σ w_b · metric_b / pair_rows_b;
- utilization: weighted by each class's share of kernel time, Σ w_b · elapsed_b / pair_rows_b.

Profiled clocks were 796 to 831 MHz under Nsight's base clock control. These are attribution numbers and must never be combined with wall times.

## Per-class results (L4)

Units:
- **w %:** share of D5 pair evaluations.
- **winst/pair:** warp instructions per pair evaluation.
- **µs/kpair:** profiled kernel time per 1000 pairs, in µs.
- **iss %:** `smsp__issue_active`.
- **FP32 %:** (fadd + fmul + 2·ffma) / (time × 58 × 128 × 2 × clock).
- **xu %, L1 %, warps %:** Nsight utilization percentages.

| point | class (b, L, Lf) | n_real | w % | field winst/pair | field µs/kpair | field iss % | field FP32 % | field L1 % | field warps % | analytic winst/pair | analytic µs/kpair | analytic iss % | analytic FP32 % | analytic xu % | analytic warps % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p00 | 0,16,16 | 10 | 1.44 | 6294 | 41.9 | 82.0 | 27.4 | 63.5 | 65.0 | 28255 | 224.6 | 70.0 | 31.8 | 78.7 | 32.4 |
| p01 | 1,16,16 | 12 | (continuity) | 6280 | 42.5 | 80.4 | 29.2 | 74.8 | 64.9 | 33704 | 267.1 | 70.0 | 31.9 | 79.0 | 32.4 |
| p02 | 1,16,16 | 14 | 6.41 | 7748 | 51.8 | 81.2 | 25.7 | 72.0 | 64.9 | 39154 | 309.2 | 70.1 | 31.9 | 79.2 | 32.4 |
| p03 | 2,16,24 | 16 | 3.12 | 6998 | 48.9 | 77.7 | 29.2 | 86.3 | 64.5 | 44617 | 340.9 | 70.0 | 31.9 | 79.3 | 32.4 |
| p04 | 2,24,24 | 18 | 15.24 | 7787 | 62.0 | 66.4 | 23.9 | 74.7 | 48.7 | 50056 | 393.4 | 70.1 | 31.9 | 79.4 | 32.4 |
| p05 | 3,24,24 | 21 | 20.50 | 9237 | 78.8 | 63.3 | 21.1 | 68.4 | 48.7 | 58231 | 456.2 | 70.1 | 32.0 | 79.5 | 32.4 |
| p06 | 4,24,32 | 24 | 4.29 | 8496 | 89.1 | 51.3 | 20.2 | 70.0 | 32.5 | 66413 | 521.4 | 70.0 | 31.9 | 79.5 | 32.4 |
| p07 | 4,32,32 | 26 | 13.98 | 9283 | 102.4 | 48.6 | 18.4 | 65.8 | 32.6 | 71858 | 561.2 | 70.0 | 32.0 | 79.6 | 32.4 |
| p08 | 5,32,32 | 29 | 16.59 | 10735 | 123.3 | 46.8 | 16.5 | 59.9 | 32.8 | 80032 | 625.2 | 70.0 | 32.0 | 79.6 | 32.4 |
| p09 | 6,32,40 | 32 | 3.12 | 9986 | 108.6 | 48.3 | 19.6 | 74.0 | 32.5 | 88212 | 689.5 | 69.9 | 32.0 | 79.6 | 32.4 |
| p10 | 6,40,40 | 35 | 9.97 | 10775 | 125.2 | 46.2 | 18.5 | 71.5 | 32.8 | 96384 | 862.6 | 60.8 | 27.8 | 69.3 | 16.7 |
| p11 | 7,40,48 | 39 | 2.34 | 12226 | 255.7 | 25.8 | 9.7 | 38.6 | 16.5 | 107320 | 958.4 | 61.0 | 27.9 | 69.5 | 16.7 |
| p12 | 7,48,48 | 42 | 1.66 | 12272 | 263.7 | 25.0 | 10.0 | 40.8 | 16.6 | 115495 | 1028.7 | 61.0 | 27.9 | 69.5 | 16.7 |
| p13 | 8,48,56 | 45 | 0.78 | 13724 | 299.4 | 24.6 | 9.3 | 38.2 | 16.6 | 123638 | 1101.3 | 61.1 | 28.0 | 69.6 | 16.7 |
| p14 | 8,56,56 | 48 | 0.45 | 12975 | 289.2 | 24.1 | 10.1 | 42.4 | 16.6 | 131876 | 1174.0 | 61.1 | 28.0 | 69.7 | 16.7 |
| p15 | 9,56,56 | 50 | 0.11 | 13764 | 309.0 | 23.9 | 9.8 | 41.5 | 16.6 | 137282 | 1222.6 | 61.2 | 28.0 | 69.8 | 16.7 |

Registers are constant: 64 per thread for field and 118 for analytic at every point.

## Work-weighted aggregates next to the 12-atom launch

| | field, D5-weighted | field, 12-atom (p01) | analytic, D5-weighted | analytic, 12-atom (p01) |
|---|---|---|---|---|
| warp instructions per pair | 9381 | 6280 | 68526 | 33704 |
| FP32 FLOP per pair | 2.20e5 | 1.47e5 | 2.06e6 | 1.01e6 |
| XU warp instructions per pair | 445 | 267 | 9734 | 4751 |
| kernel time per pair (profiled clock) | 99.8 ns | 42.5 ns | 553.8 ns | 267.1 ns |
| issue active % | 50.4 | 80.4 | 67.7 | 70.0 |
| FP32 % of peak | 18.3 | 29.2 | 30.9 | 31.9 |
| FMA pipe % | 32.5 | 46.5 | 47.2 | 48.7 |
| XU pipe % | 19.1 | 27.4 | 76.9 | 79.0 |
| L1TEX % | 63.8 | 74.8 | 16.9 | 17.3 |
| warps active % | 36.2 | 64.9 | 28.4 | 32.4 |

## What changes with size

**Field: occupancy falls as launch width grows.**
- Warps active falls from 65 % (width 16, or L=16 with L_field_width=24) to 49 % (24), then 33 % (L_field_width 32 to 40), then 17 % (L_field_width ≥ 48).
- Registers stay at 64, so the limit is shared memory or stage width, not registers.
- Issue utilization falls with it: 80 %, then 65 %, then 48 %, then 25 %.
- The 12-atom launch is therefore the field kernel's best case. Across D5, the field kernel is limited by latency and occupancy at about 50 % issue, not issue-bound at 80 %.
- At L_field_width ≥ 48, the field kernel spends about 1.8× the time per instruction it does at L_field_width 40 (p11 against p10).

**Analytic: the bottleneck stays the same.**
- It stays XU-bound at about 79 % XU and 70 % issue up to width 32.
- At L ≥ 40, warps active halves (32 % to 17 %) and XU falls to 69 %.
- Instructions per pair are close to linear in real atoms: about 2,700 warp instructions per atom.

**Real-atom count at a fixed width does matter.** At L=16, going from 12 to 14 atoms adds 23 % to field instructions and time.

**Narrow groups change the cost.**
- p03 (16 atoms at L=16, L_field_width=24) uses fewer field instructions than p02 (14 atoms at L=16, L_field_width=16), because L_field_width selects a coarser field spacing.
- A ladder taken from a small corpus alone (the internal tuning corpus: no narrow groups) would misstate about 14 % of D5's pair evaluations.

## Files

- `ladder-summary.json`: per-point raw counts under the August names (`dram__bytes_op_read.sum` is null on AD104, with `dram__bytes_read.sum` beside it), `pair_rows`, `mean_library_real_atoms`, the query set, `elapsed_s`, `sm_clock_hz`, and the D5 weights with their derivation, class assignment and work-weighted aggregates.
- In the internal development record: `<point>/` (the same layout as the single profile; `<arm>.ncu-rep` zstd-compressed, `SHA256SUMS` over the uncompressed bytes), `roofline-ladder.tsv`, `d5-pair-weights.json` and `run.log` (preflight: card idle, per-device GPU lock held).
