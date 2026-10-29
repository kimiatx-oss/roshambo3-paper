---
id: T292
title: Format-3 builder feature table -- per-molecule (type, heavy-atom indices), derived positions, self-overlaps from stored coordinates
phase: 3
lane: data
status: closed
model: opus
depends_on: [T270, T284, T287, T290, T291]
priority: high
branch: ticket/T292-builder-feature-table
worktree: <worktree>
artifacts: results/T292/
---

## Context

Format 3 (`tickets/T281-corpus-format-3.md`, design point 3) stores each
molecule's color features once, as `(type, heavy-atom indices)`. Pseudo-atom
positions are derived at load from the decoded heavy-atom coordinates. Feature
perception runs at build time only, never at screen time.

The reconstruction is measured (`results/T281/derive_h.py` and
`results/T281/README.md`, 13,500 sampled LIT-PCBA conformers):
* no feature references a hydrogen;
* every feature count matches;
* integer centroids of stored int16 coordinates reproduce the stored
  pseudo-atoms exactly in 91.2% of (conformer, type) sets, and within one
  quantum in the rest.

The builder today stores pseudo-atom coordinates per conformer. This ticket
replaces them with the per-molecule table, records the definition text, and
computes the stored self-overlaps from the coordinates the reader will recover.

**Gate.** This ticket is blocked until the author (a) approves the T282-T302 ticket
set and (b) certifies T270 done. It also depends on:
* **T291:** atom order and its permutation;
* **T287:** descriptor schema and definition capture;
* **T290:** the derived-versus-stored color go/no-go measurement. If T290 says
  no-go, this ticket stores color coordinates and *also* the table, as T281
  design point 3's fallback states.

* **T284:** `doc/FORMAT.md` (feature-table byte layout, the rounding rule) and
  the pure-Python reference decoder `src/roshambo3/format/r3g/reference.py`,
  which is this ticket's oracle. Do not start before T284 has landed.

## Scope

1. **Feature plan for every generator.**
   * The default path is `RDKitPharmacophoreGenerator.make_feature_plan`
     (`pharmacophore.py`). It returns an `RDKitFeaturePlan` of atom-id tuples
     and types, and `color_atoms_from_plan` places features at the mean of
     those atoms' coordinates.
   * The plan exists **only for the default fdef**: `make_feature_plan` returns
     `None` unless `_default_feature_plan`, which is set in `__init__` when
     neither `features` nor `fdefName` is given.
   * Extend the plan to custom fdefs, and to `CustomSMARTSPharmacophoreGenerator`,
     which places features with `compute_match_centroid`.

   Format 3 records one positioning rule: an **equal-weight** mean of the listed
   atoms. A custom fdef that declares unequal weights is **refused at build
   time** (`BuildRefused` naming the family and the weights); weights are never
   stored.
2. **Two remaps.**
   * **H-bearing to heavy.** Plan atom ids index the **H-bearing** molecule,
     because perception runs before H removal (`_prep_one`). Map them to
     heavy-atom indices after `strip_hydrogens`.
   * **Heavy to canonical.** Then map through T291's canonical-SMILES
     permutation.
   * **Refuse hydrogens.** Refuse (a `BuildRefused` naming the molecule and the
     family) any feature that references a hydrogen. None do under BaseFeatures
     (`results/T281/derive_h.py`), but a custom definition could.
3. **Derived positions.** A feature's position is the integer mean of its atoms'
   stored int16 coordinates (step units), rounded half away from zero. The exact
   arithmetic is in `doc/FORMAT.md`, and T284's pure-Python reference decoder is
   the oracle.

   Single-atom features copy the atom's coordinate exactly. Per-molecule counts
   per type replace the per-conformer `counts` columns 1..n_types. The kernel's
   per-conformer count word is rebuilt by the decoder (T285), not stored per
   conformer.
4. **Self-overlaps from stored coordinates.** T208's stored-frame contract:
   values describe exactly what the reader recovers.
   * **`vaa`:** `prep/conformer.py::stored_self_volume` on the dequantized
     heavy-atom coordinates, as T291 leaves it.
   * **`color_self`:** `backend/cpu.py::prepare_combo_library_self_overlaps`, on
     the heavy atoms plus the **derived** pseudo-atoms, dequantized at the D034
     step. Today this is computed at gather from stored coordinates
     (`prep/build.py`, the color-self path around `_color_self_values` and
     `_color_self_plan`); `_color_self_plan` builds only for a canonical
     interaction matrix. **Keep that rule** (a non-canonical matrix gets no
     stored `color_self`; the CPU path recomputes as today).
5. **Definition capture.** Write the definition **text** (the fdef file contents
   or the SMARTS list), family selection, positioning rule, numbering,
   interaction matrices r and p as values, and the RDKit version into the
   descriptor fields T287 defines. Today `_manifest` records only `fdef_path`,
   an absolute path into the build environment, which T281 calls out.

   A build from the user's own definition file needs no trust flag; print the
   definition's hash at the end of the build (T281 design point 11, "Trust UX").

6. **Stored color coordinates (`.cxyz`).** T291 keeps writing them. If T290's
   gate passed (derived color), stop writing `.cxyz` here and remove its sort
   from T291's unit-close path; if it failed, keep them and store both, per the
   fallback above. Record which in `results/T292/README.md`.

## Deciding measurement

Re-perception reproduces the table. For a sample of at least 10,000 conformers
across PUR2 (DUD-Z source SDFs under `<corpora>/`) and a LIT-PCBA slice
(source SDFs under `<corpora>/`), rebuilt by this branch:
* parse each molecule's stored SMILES, run `Chem.AddHs`, and perceive features
  with the stored definition text;
* remap to slot order, and compare with the stored table.

The comparison must be identical for 100% of molecules. Then compute positions
from the stored coordinates with T284's reference decoder and compare with the
builder's own derived positions; they must be bit-identical.
`results/T281/derive_h.py` is the method to adapt.

## Acceptance

* The deciding measurement holds, with the script under `tickets/T292/` and its
  output under `results/T292/`.
* Tests cover:
  * the default fdef;
  * a custom fdef whose families and order differ;
  * `CustomSMARTSPharmacophoreGenerator`;
  * refusal of an H-referencing feature;
  * refusal of unequal weights.
* For PUR2 rebuilt at the D034 step, the per-(conformer, type) agreement between
  derived positions and the format-2 stored pseudo-atoms (quantized to the same
  step) is reported in the `results/T281/README.md` style:
  * single-atom features exact;
  * centroid features within one quantum.

  This is evidence for NUMERICS_POLICY §4g (written in T298), not a gate here.
* `vaa` and `color_self` recomputed by an independent fp64 path
  (`roshambo3.reference.overlap.self_overlap`) from the decoded coordinates
  agree to within relative difference **p99 <= 1e-6 and max <= 1e-5**: the
  native recompute's measured scatter in `results/T208/CONTRACT.md` is 2.4e-7
  median / 1e-6 p99 relative, and the stored f32 rounding adds <= 6e-8.
* `pytest tests/test_prep*.py -q` is green on the integration branch.

## Traps

* **Re-perception requires hydrogens.** Without `Chem.AddHs`, BaseFeatures
  finds the wrong Hydrophobe set for 13,183 of 13,500 sampled conformers; with
  it, every set matches (`results/T281/derive.py` against `derive_h.py`). The
  spec, the builder's self-check and any query featurization from a stored
  definition must all add hydrogens first.
* **Two index spaces, then a third.** Atom ids from the factory index the
  H-bearing molecule. Heavy indices come after `RemoveAllHs`. Slot indices come
  after T291's canonical permutation. An off-by-one remap silently moves
  features onto neighbouring atoms, and positions stay plausible.
* **Do not perceive at screen time.** The load path does a gather and integer
  mean only. Anything that calls RDKit while decoding a library is a bug, and a
  T281 design point 11 security concern.
* **`_color_self_plan` builds only for canonical matrices.** Keep it; changing
  it is a numerics decision outside this ticket.
* **Pitfall 22.** Rebuilt corpora go under `$ROSHAMBO3_CORPORA`, out of place.

## Working rules

See `tickets/CONVENTIONS.md`.
* **Branches.** Branch `ticket/T292-builder-feature-table` from
  `ticket/T281-format3-switch` (T282 creates it from main; if absent,
  `git branch ticket/T281-format3-switch main`), and merge back into it. Worktree
  `<worktree>`.
* **Venv.** Run this worktree's code; verify `roshambo3.__file__`.
* **GPU.** No GPU is needed.

## Amended by T284 (2026-10-18): the sort rule, unequal weights, canonical matrices, `color_self`

* **Canonical feature order is in scope.** After the two remaps of scope item
  2, sort each molecule's features by `(type, atom tuple)` with atoms sorted
  ascending within a feature and duplicates kept (`doc/FORMAT.md` section 8.1
  rule 4; `reference.canonical_feature_order` is the oracle). This permutes
  today's within-type slot order and is a declared numerics component of its
  own (D034 item 4; T298's 4g measures it separately), so expose a
  builder switch, for T298's measurement only, that keeps RDKit's enumeration
  order within a type.
* **Unequal weights are refused at build** (`BuildRefused` naming the family
  and the weights; FORMAT.md Appendix B.11, **pending the author**). `positioning`
  is the one-value enumeration `"centroid"`; no weights are stored.
* **One definition of "canonical matrices"** (FORMAT.md section 18.2): exact
  float32 `r[t][t] == p[t][t] == 1` for `t >= 1` and every other entry of both
  matrices, row and column 0 included, exactly zero.
  `numerics.check_interaction_matrix` must agree with it on every matrix the
  format can carry -- today it ignores row and column 0, tests `p` only off
  the diagonal and uses `allclose` -- so either align it or wrap it with the
  exact test (`reference.canonical_matrices`) wherever the builder decides
  whether to store `color_self`.
* **`color_self` is optional** (section 18.2): omit it for a non-canonical
  matrix (this ticket's rule, kept) and when T293's `--no-color-self` says so;
  when present the matrices must be canonical. `vaa` is always present.
* The feature-atom index space is 0-based heavy indices in canonical SMILES
  order; types are 1-based (`color.types[t - 1]`); at most 16 atoms per
  feature, 255 features per type and per molecule.


**Derived color is settled (the author, 2026-10-20; D034 item 4):** T290's isolated
producer test failed its gate (0.60x), but whole-system throughput was 0.99-1.00x
stored with identical outputs, and derived color is the release layout. This
ticket is not blocked; there is no stored-color fallback to build.
