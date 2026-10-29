---
id: T298
title: The format-3 switch -- record the remaining declared changes, migrate the tests, delete the legacy format code, merge the integration branch
phase: 3
lane: infra
status: closed
model: sonnet
depends_on: [T270, T282, T289, T294, T295, T296, T297, T299]
priority: high
branch: ticket/T298-format3-switch
worktree: <worktree>
artifacts: results/T298/
---

## Context

**Gate.** Do not start until the author has approved the T282-T302 ticket set **and**
certified T270 done. It needs T299 (the rebuilt test fixtures and
the attribution corpora: the 12 DUD-Z targets and the PubChem 150K panel used by
scope item 1); T302 (the remaining rebuilds) is not needed. It also needs T289's
Linux aarch64 CI job, a blocking platform below.

**Staffing.** Model tier sonnet, run as 2-3 agents split by test cluster
(builder/format, engine/CPU/GPU, web/results/bench), with one of them coordinating.
Scope item 1 (the NUMERICS_POLICY entries) needs numerics judgment: give it to the
coordinating agent and have the author review the two entries.

Format 3 is a hard compatibility break (`tickets/T281-corpus-format-3.md`, "Why"):
nothing in the old format stays readable on main. The additive pieces (T282-T290:
spec, reference codec, native codec, validator, descriptor, definitions, fuzzing,
gating measurements) landed on main; the switch pieces (T291-T297: step constants,
builder, GPU source, CPU workers, results) landed on the integration branch
`ticket/T281-format3-switch`. This ticket finishes the switch on that branch:
record the two remaining declared numerics changes, point the test fixtures at
rebuilt corpora, migrate every corpus-touching test, delete the legacy format code,
tag the last format-2 main, and merge the integration branch into main.

T282 classified every corpus-touching test, helper and bench script (plus the
out-of-census files its 2026-10-17 review added, marked `†`) into five classes
(synthetic, external-fixture, internals, legacy-only, helper), each with a target
action and an owner ticket, in `results/T282/test_migration_matrix.md`. That
matrix is the work list; its "Summary" tables are the counts -- read them there
rather than from this ticket. The rows owned by T291-T297 are done by those
tickets; this ticket does the T298 rows and verifies the rest.

## Scope

**Handed over by T293 (merged 2026-10-21).** The builder now refuses the
measurement-only `_feature_order="enumeration"`, so the declared-change arm
that builds with today's (RDKit enumeration) feature order cannot be built on
the integration branch: build it from a checkout of `205a5569` (the integration
branch just before T293). `read_feature_table`, used by
`tickets/T292/compare_format2.py` and `reperceive.py`, no longer exists; port
those scripts to the format-3 reader if you reuse them. `prep/build.py` still
imports `quantize`, `COORD_SCALE` and a few helpers from `format/rsb3.py`; move
them before deleting that module.


1. **Declared numerics changes 4f and 4g, before the merge.** T296 wrote
   `doc/NUMERICS_POLICY.md` section 4e (the step) from T283's rung-1/rung-2
   artifacts (rung 1 = format 2 at 0.001 A; rung 2 = format 2 at 2^-8 with the
   device at 2^-8). This ticket measures **rung 2 -> rung 3** (rung 3 = format 3 on
   this branch) and writes:
   - **4f tie order**: on the PubChem 150K shape panel and the 12 DUD-Z targets of
     `results/T281/quant-sweep/PROTOCOL.md` (PUR2, HMDH, CXCR4, FABP4, ADA, AMPC,
     MAPK2, ANDR, PARP1, RENI, EGFR, HS90A), rebuilt in format 3: shape scores are
     identical per `(mol_id, conf_idx)` to rung 2; only the order within float ties
     moves (corpus order is content-defined, T281 design point 5). Record the tie
     count and the number of reordered ranks.
   - **4g derived centroids**: color pseudo-atoms derived from heavy atoms (design
     point 3) versus rung 2's stored pseudo-atoms quantized at 2^-8: single-atom
     features exact, centroids within one quantum (method:
     `results/T281/derive_h.py`, adapted); combo-mode movement on the 12 targets
     recorded with the protocol's R1-R3 reading.
   Join every comparison on `metrics/ranking.py::canonical_ids(mol_id, conf_idx)`,
   never on gid (gids differ by construction). PubChem-tier ids follow T278's
   convention; join those on `ext_id` if the rung-2 artifacts used another
   `mol_id`. Rung-2 artifacts are T283's (`results/T283/`); do not rebuild them.
   Results in `results/T298/ladder.md` + JSON, quoted verbatim in 4f/4g.
2. **Fixtures.** `tests/conftest.py` corpus fixtures (`_corpus_or_skip`,
   a 2K-molecule smoke corpus, two internal-corpus fixtures, `dudez/color_rsb3/PUR2`, around
   `:81-138`) point at the format-3 rebuilds from T299 (directory names
   under `$ROSHAMBO3_CORPORA/format3/`; read `results/T299/corpora.jsonl`). Update
   the docstrings' counts (blocks, straddling molecules -- molecules no longer
   straddle blocks). Remove every strict-xfail mark T296 added
   (`reason="format-2 fixture; T298 switches to T299 part (a) rebuilds"`, exactly as
   T296 scope 4 writes it), and the strict-xfail marks T296 may have put on tests
   in files T293 rewrote or deleted; those tests must pass, not skip.
3. **Tests**, per the matrix row's target action, not per class: `port` rows keep
   their assertions behind the new reader or the rebuilt fixtures;
   `port-new-expected-values` rows (synthetic ones included, e.g.
   `test_cpu_public_fast_defaults`, `test_cpu_worker_owned_scan`) port the same way
   but need new expected values, which the row names; `rewrite` rows assert what the
   row says under format 3; `delete` rows are deleted with a one-line note per file
   in `results/T298/deleted_tests.md` naming what replaced the coverage (or "none
   needed: legacy-only"), after salvaging what the row lists. Rows marked `(split)`
   have parts with different fates. Also from the matrix: update the comments citing
   `tests/test_color_plane_order.py` at `src/roshambo3/pharmacophore.py:59` and
   `src/roshambo3/format/dataset.py:256`, and the stale "T150 owns the rebuild"
   sentence in `tests/test_backend_boundary.py:308` (the rebuild is T299/T302).
4. **Delete** (verify each path on the branch head):
   - `src/roshambo3/prep/convert.py` and the `convert` CLI command
     (`cli.py` `_cmd_convert` and its subparser);
   - `src/roshambo3/format/topology.py`, `src/roshambo3/web/topology.py`, the
     external structure index in `web/structures.py`, and the `index-structures`
     CLI command (`cli.py:~542`, `_cmd_index_structures`);
   - the legacy self-overlap route (prepared-frame / unverified `vaa`:
     `LEGACY_ACKNOWLEDGED` in `engine/cpu_self.py:~45`, `ROUTE_LEGACY_ACKNOWLEDGED`
     in `scores.py:~115`, the `stored_vaa_legacy_blocks` counter in
     `engine/engine.py:~1561`, `backend/cpu.py`'s legacy descriptor path);
   - the old reader/writer paths in `format/rsb3.py` and `format/dataset.py` (split
     color, byte shuffle, version 3 / `permuted_color_order`, the `t` plane, counts
     synthesis, missing-`features_enum` handling, `.n_real.u8` / `.n_color_by_type.u8`
     / `.mol_id.i64` / `.conf_idx.u8` sidecars), and `engine/source.py::Rsb3Source`
     (replaced by T294's `R3gSource`). `results/T281/inventory.md` lists these
     with line references on main at 541b9f53.
5. **bench/** scripts that read corpora (via `Catalog` or group internals, e.g.
   `bench/metal.py`, `bench/metal_rc.py`, `bench/apple_silicon.py`,
   `bench/audit_cpu_port.py`, `bench/scale_check.py`,
   `bench/metal_combo_provisional.py`, `bench/xcheck_roshambo2.py`): port or move to
   `tickets/<T>/` per the matrix. Recorded gid lists (e.g. `GIDS` in `bench/metal.py`)
   are re-derived from `(mol_id, conf_idx)`.
   **Archive only what nothing live imports.** `bench/metal_rc.py` (port) imports
   `dispatch`, `dump` from `bench.metal_half_precision`, `aligned`, `compare` from
   `bench.metal_quality_diagnosis` and `ranking_passes` from
   `bench.metal_torque_validation` (`metal_rc.py:17-19`), all three archived; and
   `tests/test_metal.py:674` imports `VARIANTS` from `bench.metal_combo_provisional`
   (archived). Move those six names into `bench/metal.py` first (`aligned` keys
   captures on gid; re-key it on `(mol_id, conf_idx)`), then archive. Check with
   `git grep -nE "from bench\.(metal_half_precision|metal_quality_diagnosis|metal_torque_validation|metal_combo_provisional|metal_binding_provisional|metal_cpu_rates|metal_pose_diagnosis|metal_texture|audit_cpu_port|scale_check)" -- bench tests src`
   returning nothing outside the archived set before moving them.
5b. **The T69 regression suite.** `bench/regression_suite.py` loads its tiers from
   `tickets/T69/` by path (`bit_exact` :159, `recall` :195, `throughput` :271,
   `enrichment_spotcheck` :317). `tickets/T69/recall.py` reads sidecars (:104, :220,
   :264), screens through `Rsb3Source` (:185-193) and writes gid-keyed gold
   (`results/T69/gold/recall_gold_<internal corpus>.npz`, saved with `gids` + `mol_id` at
   :224-225); `tickets/T69/enrichment_spotcheck.py` opens
   `dudez/color_rsb3_perm/<target>` (:87) and joins on gid (:106-112);
   `tickets/T69/throughput.py` opens a corpus by name (:104-130). Port the harness
   and the three tiers to the format-3 reader and `R3gSource`, and re-key the gold
   on `(mol_id, conf_idx)` (`metrics/ranking.py::canonical_ids`). The numbers in
   `results/T69/baseline.json` are format-2 numbers; T300 regenerates the baseline
   and the gold on format-3 corpora and records old vs new -- do not regenerate them
   here. `tickets/T69/` is part of the archive by convention, but these tiers are
   live code the suite imports by path (`bench/regression_suite.py:55-66`); edit them
   in place, or move them and their import path together.
5c. **Build provenance without a git repository** (the author, 2026-10-21). **Done early and merged into the integration branch at f55baaa4** (branch
   `ticket/T298a-build-provenance`, independently reviewed); nothing left to do
   here except keep `tests/test_version.py` green. The original text follows. A
   released roshambo3 is installed from a wheel or a tarball, not run from a
   checkout, so `prep.commit` (`prep/build.py`, the clean-tracking-checkout
   probe at about :2757) is `null` there. FORMAT.md §13 (Versioning policy) item 3 currently rests
   `corpus.json` byte identity on "the same `prep.version` and `prep.commit`",
   and `prep.version` is the static `__version__` string, which does not move
   when the builder changes between two dev builds.
   * **One version source.** `roshambo3.__version__` (`src/roshambo3/__init__.py`)
     and `pyproject.toml`'s `version` are two copies today. Make
     `__version__` come from `importlib.metadata.version("roshambo3")`, falling back
     to the pyproject string only when no distribution metadata exists. Add a test
     that the two agree. `prep.version` and `build.json`'s `roshambo3_version`
     keep reading `__version__`.
   * **Spec wording.** Reword FORMAT.md §13 item 3 (and the matching sentence
     in §9.2, "an identical `corpus.json` when `prep.version` and ...") so that
     rebuild identity rests on the **roshambo3 release** (`prep.version`) plus
     the RDKit and numpy versions `build.json` records. `prep.commit` is
     optional provenance when present. A dev version (a `.dev` suffix) with
     `prep.commit` null names no particular source, so state that identity is
     then claimed only for the same source tree. §10.1's field table keeps
     `prep.commit` optional. No format bytes, fingerprint inputs or validator
     rules change.
   * The CMake build stamp (`git_sha`, `cuda_src_tree`, `cuda_src_dirty`) already
     degrades to `"unknown"`/`None` without git, and `cuda_src_sha256` is
     content-based. Leave it alone; add a test that `scripts/source_stamp.py`
     produces a stamp with no `.git` (for example, from a `git archive` extract).
   T301 owns setting the version from the release tag at packaging time.
6. **Freeze and tag.** Announce a freeze on `engine/source.py`, the CPU worker loop
   in `engine/engine.py`, `prep/build.py` and `format/` while this runs. Immediately
   before merging, tag **main's** head (still format 2) `format2-last`, and create the
   frozen reference worktree
   `git worktree add <format2-last worktree> format2-last` with its own
   venv built from that worktree (`pip install -e .` inside it; check
   `roshambo3.__file__`). It is used by T300's A/B comparisons and never edited.
7. **Merge** `ticket/T281-format3-switch` into main, no-ff, after acceptance.

## Deciding measurement

The full test suite green on the integration branch head on all three platforms,
with NUMERICS_POLICY 4f and 4g written from measured rung 2 -> 3 numbers.

## Acceptance

- **Blocking platforms** (all three required before the merge):
  - Linux x86, CPU and CUDA, on roci;
  - Linux aarch64, the CI job T289 adds (`ubuntu-24.04-arm`);
  - macOS arm64: the author runs the suite from a tarball of the branch head
    (built with `git archive`, as earlier ports did) -- the merge waits for the
    author's confirmation; Metal results are recorded too if run.
  The skip count on each is recorded and compared with main's (a jump means a
  fixture is missing, not a pass).
- NUMERICS_POLICY sections 4f and 4g written with numbers quoted verbatim from
  `results/T298/ladder.md`; the author has reviewed them.
- The legacy-symbol grep, **case-insensitive**, returns nothing under `src/` and
  `tests/`:
  `grep -rniE "permuted_color_order|PERMUTED_COLOR_ORDER_VERSION|byte_unshuffle|t_all_zero|t_plane|color_rsb3|\.color\.rsb3|n_color_by_type|LEGACY_ACKNOWLEDGED|ROUTE_LEGACY_ACKNOWLEDGED|convert_corpus|index-structures|structures\.sqlite|Rsb3Reader|Rsb3Source" src tests`
  (extend the list with anything T284-T297 named as legacy; record the final list
  in `results/T298/README.md`).
- `python3 scripts/ticket_index.py --check` passes.
- `format2-last` tag and its reference worktree exist; its venv's
  `roshambo3.__file__` points inside it.
- Integration branch merged into main no-ff; `results/T298/README.md` lists deleted
  modules, line counts removed, and the per-platform test summaries.

## Traps

- **Skips are not passes.** Fixture tests skip when a corpus is absent
  (`_corpus_or_skip`); a migration that points at a wrong directory turns failures
  into skips. Compare skip counts, and read them.
- **Never join on gid across formats** in the 4f/4g measurement; corpus order changed.
- **Do not delete a legacy test whose assertion still applies** (resume, worker
  death, stereo guard, id reference, progress): those assert pipeline behavior, not
  layout, and port to format 3.
- **Tag main, not the branch.** `format2-last` must be the last format-2 main commit,
  taken immediately before the merge.
- **Main must stay green.** Merge main into the integration branch before the final
  merge; resolve conflicts in the frozen areas by taking the branch.
- **The release repos are not touched here** (T301 ports).
- The shared venv points at main from a worktree; each agent builds from its own.

## Working rules

See `tickets/CONVENTIONS.md`. Split the matrix among 2-3 agents by test cluster
(builder/format, engine/CPU/GPU, web/results/bench), each on a sub-branch merged into
`ticket/T298-format3-switch`, which merges into `ticket/T281-format3-switch`. Before
any CUDA context, export `CUDA_MPS_PIPE_DIRECTORY` to a private directory and check
`pgrep -a nvidia-cuda-mps`; take the GPU lock via `bench.gpu_lock.GpuLock` for timed runs
and for the ladder screens. Never copy corpora into a worktree
(pitfall 22).

## Amended by T284 (2026-10-18): 4g has two components, attributed separately

`doc/FORMAT.md` section 8.1 rule 4 sorts each molecule's features by `(type,
atom tuple)` (atoms ascending, duplicates kept). Within a type that is a
permutation of today's color slots (RDKit's match-enumeration order), so the
color accumulation order changes independently of the derived-centroid
change. NUMERICS_POLICY 4g therefore names two components -- (a) derived
centroids (integer mean of stored int16, at most one quantum from today's
quantized centroid) and (b) the canonical within-type feature order -- and
the rung 2 -> 3 ladder attributes them separately: build the rung-3 arm once
with the sort and once with today's order (a builder switch T292 exposes for
the measurement only), and quote both deltas. D034 item 4 declares
both components.
