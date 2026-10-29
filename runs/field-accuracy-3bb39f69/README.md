# Field* cells at 3bb39f69, format 3 (roci, 2026-10-23)

References to `results/`, `tickets/`, `doc/`, `hosts/` and other files not in this repository point at the internal development record.

> **Paper import.** Only `summary.json`, `per-query.json` and this README are archived here, with local paths and GPU identifiers redacted. The query SDF (an internal tuning panel), the driver scripts, the raw run records and the preflight files this README cites stay in the internal record. The paper's Field* cells use the shipped default update rule: the `ADAGRAD_EXP`, first-300,000 row in `summary.json` → `alternates`. The `ADAGRAD_QADD` row (`rows[0]`, T36's settings) is kept for continuity. Internal panel record names are replaced by `query-NN` (the query index).

Main results, field retrieval: FIELD pose search against ANALYTIC pose search, re-measured at the
frozen benchmark commit `3bb39f698bfffc1045f585187d30230ba639a758` on the format-3 internal tuning corpus,
with T36's definitions (`tickets/T36/accept_t36.py`, `results/T36/accept_t36_q32.json` in the
internal repo). Measured on 2026-10-23. Accuracy work: untimed, but both roci GPU lock
families were held for each run (`preflight-*.txt`), and no profiler was running.

## The four cells

Primary row (`summary.json` `rows[0]`): format-3 group 5, first 300,000 conformers, T36's
optimizer exactly (25 steps, `lr_t` 0.4, `lr_q` 0.1, `start_mode` 1 = 4 starts, `opt_mode` 0 =
`ADAGRAD_QADD`), h = 0.5 Å.

| macro | manuscript (T36, format 2) | **3bb39f69, format 3** | shipped update rule (`ADAGRAD_EXP`) |
|---|---|---|---|
| `FieldPanelRecallAtThousandPercent` | 99.45 | **99.48** | 99.52 |
| `FieldWorstRecallAtThousandPercent` | 98.4 | **98.6** | 98.7 |
| `FieldPanelTopHundredSetPercent` | 99.34 | **99.22** | 99.19 |
| `FieldMedianPoseRmsdAngstrom` | 0.017 | **0.017** (0.01652) | 0.016 (0.01650) |

All four rows pass T16's gate (worst recall@1000 ≥ 0.98, panel top-100 ≥ 0.99). The differences
from the manuscript are +0.03 / +0.2 / −0.12 points and 0.00004 Å. They are within the
query-to-query spread (per-query recall@1000 runs 0.986 to 1.000).

Per-query recall@1000, primary row, sorted: 0.986, 0.988, 0.988, 0.989, 0.990, 0.990, 0.991,
0.992, 0.992, 0.993, 0.993, 0.993, 0.994, 0.995, 0.995, 0.996, 0.997 ×5, 0.998 ×5, 0.999 ×5,
1.000. Median 0.9965, p10 0.9891. The worst query is `query-18`. T36's worst was `query-24`
(0.984), which scores 0.988 here. As in T36, recall falls with query size. `per-query.json` has every query against T36's value.

## Other populations (`summary.json` `alternates`)

| population | update rule | n_conf | mean / worst recall@1000 | top-100 | median pose RMSD |
|---|---|---|---|---|---|
| group 5, first 300k | ADAGRAD_EXP | 300,000 | 99.52 / 98.7 | 99.19 | 0.0165 (all pairs) |
| group 5, whole | ADAGRAD_QADD | [withheld] | 99.49 / 98.2 | 99.25 | 0.0167 (all pairs) |
| group 5, whole | ADAGRAD_EXP | [withheld] | 99.48 / 98.5 | 99.25 | 0.0167 (all pairs) |
| whole corpus, top-10,000 | ADAGRAD_QADD | [withheld] | 99.63 / 99.0 | 99.59 | 0.0115 (matched hits) |
| whole corpus, top-10,000 | ADAGRAD_EXP | [withheld] | 99.68 / 99.0 | 99.69 | 0.0114 (matched hits) |

The whole-corpus rows use the shipped per-bucket lattice spacing (0.4 Å at L ≤ 24, 0.5 at L = 32,
0.6 at L ≥ 40), not a uniform 0.5. Their RMSD is the median over hits retained by both arms
(about 319k of 320k pairs), because an all-pairs median cannot be computed from retained lists. It
is not the same statistic as the paper's cell. The dense rows report both: the matched-hit
median in group 5 is 0.011–0.012 Å.

## Identity

- **Build:** `$EXTERNAL_DATA` (site-packages `roshambo3`). The
  stamp is `git_sha` 3bb39f69…, Release, sm_120, nvcc 13.2.86, `cuda_src_sha256`
  402af23d…, `cuda_src_dirty` False. The full `BuildInfo` is in `summary.json`.
- **Corpus:** the internal tuning corpus (format 3). Its path, `corpus.json` sha256, fingerprint
  and populations are [withheld].
- **Subset (primary):** format-3 group index 5 (bucket 4, L = 32; file name, population and header
  hash [withheld]). The subset is its first 300,000 conformers in file order (global-id interval
  [withheld]).
- **Queries:** 32 queries from an internal query panel, the same panel and selection as T36
  (panel hash, population and selection rule [withheld]). The selected heavy-atom counts match
  T36's `query_n_real` exactly.

## How this differs from T36

1. **Subset membership.** T36 used the first 300,000 rows of format-2 group 5, which is also
   bucket 4 / L = 32 but has a different population. The format-2 bulk files are gone and only
   `ids.i64`/`meta.parquet` remain, in molecule order rather than group order, so that subset's
   membership cannot be rebuilt. The format-3 rule keeps the same group index, bucket, width,
   count and "first rows". The whole-group and whole-corpus rows show the cells do not depend on
   that choice.
2. **Coordinates.** Format 3 stores bp256 coordinates (step 2^-8 Å), whereas format 2 used int16 at 0.001 Å. The queries are prepared by roshambo3's
   own `load_queries`, not roshambo2's `prepare_from_rdkitmols`.
3. **Kernels.** The reference is roshambo3's `PoseSearch.ANALYTIC` and the arm is its
   `PoseSearch.FIELD` at 3bb39f69, not T36's `blockwise_tiled_t27` / `blockwise_grid_t36`.
4. **Update rule.** The primary row uses T36's `opt_mode` 0 (`ADAGRAD_QADD`), as instructed. The
   shipped default at 3bb39f69 is `ADAGRAD_EXP` (T45), which is the second column above. Both
   arms always use the same rule.
5. **Tie-break.** Ties are broken by ascending global conformer id
   (`roshambo3.numerics.rank_order`), the product's rule. Inside one group this is exactly T36's
   stable argsort by row index. It is not METRICS.md §2's `canonical_ids(mol_id, conf_idx)`:
   format-3 `mol_id` is a hash and does not increase with gid. The two can differ only on an
   exact float32 tie at the 100th or 1,000th place.
6. **Metrics source.** Recall and top-100 come from `roshambo3.metrics.recall.recall_at`. Pose
   RMSD is computed by the driver, with the `ScreenResult.aligned_poses` transform convention.
   T36's `posed` applied the start rotation transposed, which gives the same result for the
   identity and 180° start rotations.

## Files

- `field_accuracy.py` (internal record): the driver (public API: `score_matrix`, `screen`, `Catalog.coordinates`,
  `roshambo3.metrics`)
- `run.sh` (internal record): takes the locks and runs the driver
- `make_summary.py` (internal record): builds the summary and per-query files
- `dense.json` / `dense.log`, `screen.json` / `screen.log` (internal record): raw run records (settings resolved
  per arm, advisory walls, build and corpus identity)
- `summary.json`: the cells, in `accept_t36_q32.json` key names. The paper generator
  (`scripts/generate_paper_assets.py`) searches `rows` and `alternates` together for the one row
  with `population` `first300k` and `update_rule` `ADAGRAD_EXP` (an `alternates` entry) and
  requires it to pass the gate. `rows[0]` (T36's `ADAGRAD_QADD` settings) is kept for continuity.
  The record also carries the definitions, subset rule and identity.
- `per-query.json`: per-query recall@1000 and top-100 for every row, plus T36's values
- `preflight-*.txt` (internal record): GPU state and lock paths at the start and end of each run
