---
id: T303
title: Format-3 spec and reference fix round -- consolidate the T285/T286 review findings, regenerate the color conformance corpus
phase: 3
lane: data
status: closed
model: opus
depends_on: [T284]
priority: high
branch: ticket/T303-format3-fix-round
worktree: <worktree>
artifacts: results/T303/
---

## Context

T284 wrote `doc/FORMAT.md`, the pure-Python reference
(`src/roshambo3/format/r3g/reference.py`) and the conformance corpus
(`tests/data/format3/`). T285 (native codec) and T286 (Python writer, reader,
validator) implemented against them and found defects in all three; independent
reviews of T285 and T286 added more. The author chose (2026-10-18) to fix them in one
round here rather than piecemeal. Sources of every finding below: `results/T285/README.md`,
`results/T286/README.md`, and the review notes in `results/T303/reviews/` (the
T285 and T286 review reports, committed there when this ticket was filed).

**Scope note (the author, 2026-10-18).** T285 and T286 were merged to main with
these defects open (merges 92237340, 33673c82). This ticket is **not a full
hardening pass**. Every bug found is documented here exactly, with reproducers.
D034 item 10 was narrowed the same day: memory safety of native code, no
process crash on a malformed file, and isolation of custom definitions are
required; other time/memory bounds are best-effort. So:
* **Required:** Scope 1-3; T286 B1-B8; T285 D1 and D2; T286 S1 (process abort).
* **Best-effort (do if cheap, else record and leave):** T286 S2 (quadratic
  shape product -- the rank check is one line, so do it), S3 (JSON container
  limit), S5 (UTF-8), S6 (column lengths); T285 D3, D4.
* **Out of scope:** T286 S4 (scan-cache forgery); record it in FORMAT.md as a
  known limitation of the local cache.
* **Also apply D034 item 9 as amended:** `n_conf <= 4096`, so every block has
  at most 4,096 rows. Remove the single-molecule exception from FORMAT.md §6
  rule 4, change §7, §14 and §17's limits and the overflow audit
  (`results/T284/overflow_audit.md`) to match, replace the 65,535/65,536-row
  seeds with 4,096/4,097, update the reference and T285's/T286's checks, and
  restate the decoded-size caps (at most 4,096 x 512 x 6 B = 12.6 MB in the
  device layout). This supersedes the size-cap items in Scope 3.
* Rewrite limits 33/34 in FORMAT.md §14 as best-effort engineering targets.
* **`molecules.parquet` is zstd-compressed** (D034 item 11, the author 2026-10-18;
  replaces the uncompressed-only rule of FORMAT.md §11 and the security
  amendments). Writers use ZSTD; readers accept ZSTD or UNCOMPRESSED; encoding
  stays PLAIN, columns non-null, row groups <= 2^14 rows. Keep the page walk and
  the declared uncompressed-size checks as best-effort bounds. Pick the zstd
  level by measuring file size and full-read time at levels 3, 9 and 19 on
  LIT-PCBA's molecule table and on one internal library sample; record it in `results/T303/`. Update FORMAT.md §11, the reference
  writer and validator, T286's `parquet.py`, the `parquet_compressed` seed
  (now legal: replace it with an unsupported-codec seed, e.g. SNAPPY), and
  T293's writer text.

**Gate.** Approved by the author as part of the format-3 work (additive: spec text,
reference, test data; no change to main's numerics). Does not need T270.

## Scope

1. **Regenerate the color conformance corpus.** `tests/data/format3/make_conformance.py`
   passes the already-renumbered molecule to `perceive_features` and then maps
   the atom ids through `perm` a second time, so 12 of the 47 molecules in
   `color/` carry wrong feature tables (`verify --tier deep --all` refuses
   `color/` with `layout.features`; `open`/`scan` accept it). Fix the double
   permutation, regenerate, and update `EXPECTED.json` (feature, merged, pseudo,
   color_self and file digests change). The probes that showed it are in
   `tickets/T286/`.
2. **Reference feature-order check.** The reference `scan` pads atom tuples with
   256 when checking §8.1 rule 4, so a tuple that is a prefix of another sorts
   last; the spec and `canonical_feature_order` sort it first, and the
   reference refuses its own writer's output. Pad with -1 (as T286's validator
   does) and add a seed/test with a prefix tuple.
3. **Spec inconsistencies** (fix the text; each one names the choice the
   implementations already made -- keep it unless a review says otherwise):
   * §16.5 lacks codes for refusals T285 and T286 must make. Add them:
     `decode.*` (T285, `results/T285/README.md`), `validation.scan_required`,
     `value.self_overlap`, and the uses of `limit.smiles`, `layout.features`,
     `internal.error` listed in `results/T286/README.md` "Decisions".
   * Decoded-size caps: §6 rule 4 and §14.2 say 100.7 MB / 201 MB, Appendix B.7
     says 128 / 256 MiB. Make them agree with the overflow audit
     (`results/T284/overflow_audit.md`).
   * GPU tile padding takes a 65,535-row block to 65,536 rows, slightly past
     §14.2's bound; state the padded bound (T294 sizes the pinned pool with
     `native.gpu_layout_elements`) and the CPU float32 maximum (~403 MB).
   * Refusal code for a run slice that does not sum to the block's rows:
     validator `layout.runs`, native `layout.blocks`. Pick one; align both.
   * Limit 4 (JSON string length): the spec counts raw bytes including escapes,
     the reference counts an escape as one byte. Follow the spec in the
     reference.
   * §5.6 says `deep` refuses `min + u` overflow; B.27 dropped that check.
     Remove it from §5.6.
   * Check order: §3.5 puts the fingerprint before the blocks hash; §16.2 and
     the reference after the block walk. Make §3.5 match.
   * `build.json`: §12.1 says a corpus never fails for it; §16.4 item 5 refuses
     an unparsable one. Decide (recommend: §16.4 wins, §12.1 reworded).
   * Seeds carry placeholder `vaa` values; document the `deep` item ordering
     T286 relies on so every seed is wrong in exactly one way at its tier.
4. **Review findings** from the independent T285 and T286 reviews,
   `results/T303/reviews/T285-review.md` and `T286-review.md` (reproducers in
   `t285-repro/`, `t286-repro/`). Fix every confirmed defect; for judgment calls,
   fix or record why not. Security items first:
   * T286 S1: one byte in `molecules.parquet` aborts the process (SIGABRT inside
     pyarrow's footer parse, SizeStatistics histogram). Walk the parquet footer
     against a closed schema before any pyarrow call; FORMAT.md §11 step 2.
   * T286 S2: quadratic section-shape product at `open` (19-21 s from a 2 MB
     header). Check shape rank before the product, in V and R.
   * T286 S3: a legal-size JSON document exceeds limit 34 (416 MiB). Add a JSON
     container-count limit.
   * T286 S4: post-scan edits reach consumers, and the scan cache can be forged.
     Bind the cache to content, harden its directory, and re-check atom indices.
   * T286 S5/S6: UTF-8 validity and column lengths at scan; read `rotors`.
   * T285 D1: double fetch of `feature_atom_offsets` (`r3g_codec.cpp:348`), an
     over-read reachable through aliased outputs or a concurrent writer.
     Re-check at the use site, and refuse overlapping output buffers.
   * T285 D2: `native.py` allocates from unchecked `rows`/`L`. Check §14 limits
     before allocating.
   Then the T286 correctness items (B1-B8), the T285 D3/D4 items, and the
   FORMAT.md text changes both reviews propose (codes, size caps, check order,
   §12.1, §16.1).
5. **Re-run the implementations against the regenerated corpus.** T285's
   digest tests (all ISA paths available locally: scalar, AVX2; NEON under
   `qemu-aarch64-static` as `results/T285/README.md` describes) and T286's
   suite, including `verify --tier deep --all` on both conformance corpora.
   Flip T286's `test_conformance_color_corpus_feature_tables_disagree_with_reperception`
   to assert acceptance.

## Deciding measurement

`verify --tier deep --all` accepts both conformance corpora; reference, native
(every locally executable ISA) and T286 agree on every digest and on every
seed's tier and code.

## Acceptance

* `tests/test_format3_reference.py`, T285's and T286's tests pass;
  `pytest -k "not cuda"` has no new failures (the pre-existing
  `test_prepare.py::TestRoundTrip::test_the_vaa_sidecar_matches_a_recomputed_self_overlap`
  failure predates format 3 and is not this ticket's).
* Conformance regeneration is byte-identical on a second run.
* Every item in Scope 3 and 4 is fixed or has a written reason in
  `results/T303/README.md`.
* FORMAT.md Appendix B gains a dated "Fix round (T303)" list.

## Traps

* The color digests in `EXPECTED.json` matched three implementations only
  because all three consumed the same wrong input; after regeneration, check
  the derived-color gather against the §8.3 formula directly, not only against
  digests.
* roci has no venv for the main checkout; build one per worktree and check
  `roshambo3.__file__` (`doc/BENCHMARKING.md`).
* Do not edit T270.

## Working rules

See `tickets/CONVENTIONS.md`. Branch `ticket/T303-format3-fix-round` from main;
additive, merges to main.

## Completion (2026-10-18)

Implemented and validated; see `results/T303/README.md` for the item-by-item
fix/defer record, regenerated corpus, ISA/sanitizer evidence and test results.
ZSTD level 9 was selected directly by the author; compression benchmarking waived.
No macOS testing was performed.
