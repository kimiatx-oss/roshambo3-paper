"""T169 third experiment: a committed, self-contained fixture of iso-step pairs.

The second experiment left one number needing an explanation.  At matched step
count -- ROSHAMBO3 at 25 against ROSHAMBO2-with-fixes at 25, both poses rescored
by the float64 oracle -- the *shape* channel is a coin flip (50.2% to ROSHAMBO3,
median +0.0000) with a left tail: 10.8% of pairs are worse under ROSHAMBO3 by
more than 0.01 and 2.1% by more than 0.05.  Aggregates cannot say what produces
that tail; individual pairs can.

This script picks the pairs and packages them so the diagnosis, and any future
re-run of it, needs nothing but the committed file: no 470 MB panel, no external
oracle directories, no ``$ROSHAMBO3_CORPORA``, no GPU.

What "self-contained" means here
--------------------------------
Every conformer either engine scored is written out in full -- its coordinates,
its color-feature coordinates, its types and its counts, under *each engine's*
own preparation, because the two engines prepare and number features
differently and a fixture that kept one of them could not reproduce the other's
number.  Every arm's raw 20-column pose row travels with it, so the pose
reconstruction is re-derivable rather than summarized, and so is every
reported and oracle-rescored score.  ``isostep_verify.py`` re-scores the whole
thing from these bytes in seconds and asserts against the recorded values.

The selection rule, stated so it can be argued with
---------------------------------------------------
Candidates are the 1,038 pairs of the second experiment's panel that both
engines score on the same heavy-atom set and that are not self-matches.  For
each of the three objectives the iso-step delta is

    delta_c  =  oracle(ROSHAMBO3 @ 25 steps, c)  -  oracle(ROSHAMBO2-fixed @ 25 steps, c)

and three outcome bins are cut on it: ``r3_better`` at ``delta >= +0.01``,
``tie`` at ``|delta| <= 1e-3``, ``r2_better`` at ``delta <= -0.01``.  The
thresholds are the ones the parent table already reports against, not new ones.

Within each of the nine (objective, bin) cells the five pairs nearest the
10th, 30th, 50th, 70th and 90th percentile of *that cell's* delta are taken.
Percentiles rather than a random draw because the cell is small enough that a
seed would decide the answer, and percentiles rather than the extremes because
the point of a bin is to be represented by its middle -- the extremes are
selected separately and labeled as extremes.  The rule is deterministic and
carries no seed.

Four pairs are then added deliberately and marked ``extreme``: the worst
ROSHAMBO3 loss in each channel (the -0.103 shape, the -0.127 color, the -0.041
combination the parent table names) and the largest shape win, as a counterweight
so the extreme set is not one-sided.  They are labeled, and no aggregate in the
diagnosis is quoted over the fixture as though it were a sample of the panel --
it is a stratified sample by construction and its bin proportions are chosen,
not measured.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CH = ("tanimoto_shape", "tanimoto_color", "tanimoto_combination")
OBJ = {"shape": "tanimoto_shape", "color": "tanimoto_color",
       "combination": "tanimoto_combination"}
BINS = ("r3_better", "tie", "r2_better")
PERCENTILES = (10, 30, 50, 70, 90)
BETTER = 0.01
TIE = 1e-3
REFERENCE_ARM = "roshambo3"
BASELINE_ARM = "r2_fixed_steps25"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def bin_of(d: float) -> str | None:
    if d >= BETTER:
        return "r3_better"
    if d <= -BETTER:
        return "r2_better"
    if abs(d) <= TIE:
        return "tie"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--rescored", required=True,
                    help="pose_rescore.py's .pairs.npz for the 25-step arms")
    ap.add_argument("--mirror", default="",
                    help="the mirror run's .pairs.npz, for the 10-step arms")
    ap.add_argument("--arm", action="append", default=[],
                    help="name=path/to/arm.npy, repeatable")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    f = np.load(a.panel, allow_pickle=True)
    z = np.load(a.rescored, allow_pickle=True)
    zm = np.load(a.mirror, allow_pickle=True) if a.mirror else None

    ok = (np.asarray(z["same_atom_set"], bool)
          & ~np.asarray(z["is_self_match"], bool))
    cand = np.flatnonzero(ok)
    delta = {name: (np.asarray(z[f"oracle/{REFERENCE_ARM}/as_built/{c}"])
                    - np.asarray(z[f"oracle/{BASELINE_ARM}/as_built/{c}"]))
             for name, c in OBJ.items()}
    log(f"[fixture] {len(cand)} comparable non-self pairs")

    # --- the nine cells ----------------------------------------------------
    picked: dict[int, list[str]] = {}
    cells: dict[str, list[int]] = {}
    for obj in OBJ:
        d = delta[obj]
        for b in BINS:
            pool = np.array([k for k in cand if bin_of(float(d[k])) == b],
                            np.int64)
            if len(pool) == 0:
                cells[f"{obj}:{b}"] = []
                log(f"[fixture] {obj:12s} {b:10s} EMPTY")
                continue
            order = pool[np.argsort(d[pool], kind="stable")]
            take = []
            for p in PERCENTILES:
                # nearest-rank percentile, deterministic and seedless
                i = int(round((p / 100.0) * (len(order) - 1)))
                if order[i] not in take:
                    take.append(int(order[i]))
            cells[f"{obj}:{b}"] = take
            for k in take:
                picked.setdefault(k, []).append(f"{obj}:{b}")
            log(f"[fixture] {obj:12s} {b:10s} pool {len(pool):4d} -> "
                f"{len(take)} pairs, delta "
                f"[{d[take].min():+.4f}, {d[take].max():+.4f}]")

    # --- the labeled extremes ---------------------------------------------
    extremes = {}
    for obj in OBJ:
        d = delta[obj]
        k = int(cand[np.argmin(d[cand])])
        extremes[f"{obj}:worst_r3_loss"] = k
    k = int(cand[np.argmax(delta["shape"][cand])])
    extremes["shape:largest_r3_win"] = k
    for tag, k in extremes.items():
        picked.setdefault(k, []).append(f"extreme:{tag}")
        log(f"[fixture] extreme {tag:28s} pair {k} delta_shape "
            f"{delta['shape'][k]:+.4f} delta_color {delta['color'][k]:+.4f} "
            f"delta_combo {delta['combination'][k]:+.4f}")

    sel = np.array(sorted(picked), np.int64)
    log(f"[fixture] {len(sel)} distinct pairs selected")

    # --- the conformers those pairs need, deduplicated ---------------------
    pq = np.asarray(f["pair_query"], np.int64)[sel]
    pl = np.asarray(f["pair_library"], np.int64)[sel]
    uq, iq = np.unique(pq, return_inverse=True)
    ul, il = np.unique(pl, return_inverse=True)
    log(f"[fixture] {len(uq)} query conformers, {len(ul)} library conformers")

    out: dict[str, np.ndarray] = {}
    for eng, side, rows in (("r2", "q", uq), ("r2", "l", ul),
                            ("r3", "q", uq), ("r3", "l", ul)):
        co = np.asarray(f[f"{eng}_{side}_coords"])[rows]
        ty = np.asarray(f[f"{eng}_{side}_types"])[rows]
        nr = np.asarray(f[f"{eng}_{side}_n_real"])[rows]
        # Trim the padding: keep only as many columns as the widest member uses.
        if eng == "r2":
            nt = np.asarray(f[f"{eng}_{side}_n_total"])[rows]
            width = int(nt.max())
            out[f"{eng}_{side}_n_total"] = nt.astype(np.int32)
        else:
            width = int(max(int(nr[i]) + int((ty[i] != 0).sum())
                            for i in range(len(rows))))
            width = max(width, int(np.max(np.flatnonzero(ty.any(0)) + 1)))
        out[f"{eng}_{side}_coords"] = np.ascontiguousarray(co[:, :width],
                                                           np.float32)
        out[f"{eng}_{side}_types"] = np.ascontiguousarray(ty[:, :width],
                                                          np.int32)
        out[f"{eng}_{side}_n_real"] = nr.astype(np.int32)

    qkeys = np.array([str(k) for k in f["query_keys"]])[uq]
    lkeys = np.array([str(k) for k in f["library_keys"]])[ul]
    out["query_keys"] = qkeys
    out["library_keys"] = lkeys
    out["pair_query"] = iq.astype(np.int32)
    out["pair_library"] = il.astype(np.int32)
    out["pair_query_key"] = qkeys[iq]
    out["pair_library_key"] = lkeys[il]
    out["pair_query_molecule"] = np.array([int(k.split("_")[0]) for k in qkeys[iq]],
                                          np.int64)
    out["pair_library_molecule"] = np.array([int(k.split("_")[0]) for k in lkeys[il]],
                                            np.int64)
    out["pair_stratum"] = np.asarray(
        [str(s) for s in f["pair_stratum"]], dtype="<U16")[sel]
    out["panel_pair_index"] = sel
    out["selected_for"] = np.array([";".join(picked[int(k)]) for k in sel],
                                   dtype="<U96")
    out["is_extreme"] = np.array(
        [any(t.startswith("extreme:") for t in picked[int(k)]) for k in sel],
        bool)
    for obj in OBJ:
        out[f"isostep_delta/{obj}"] = delta[obj][sel]
        out[f"isostep_bin/{obj}"] = np.array(
            [bin_of(float(delta[obj][k])) or "middle" for k in sel],
            dtype="<U10")

    # --- every arm's pose row and every recorded score ---------------------
    arm_meta = {}
    for spec in a.arm:
        name, _, path = spec.partition("=")
        rows = np.load(path)
        side = json.loads(Path(path).with_suffix(".json").read_text())
        out[f"pose/{name}"] = np.ascontiguousarray(rows[sel], np.float32)
        arm_meta[name] = {k: v for k, v in side.items()
                          if k not in ("launches",)}
        src = zm if (zm is not None and f"oracle/{name}/as_built/{CH[0]}" in zm.files
                     and f"oracle/{name}/as_built/{CH[0]}" not in z.files) else z
        for c in CH:
            out[f"reported/{name}/{c}"] = np.asarray(
                src[f"reported/{name}/{c}"])[sel]
            for v in ("as_built", "rigid"):
                key = f"oracle/{name}/{v}/{c}"
                if key in src.files:
                    out[key] = np.asarray(src[key])[sel]
        log(f"[fixture] arm {name}: poses and scores carried")

    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(outp, **out)
    meta = {
        "what": "T169 third experiment: iso-step outcome-stratified pair fixture",
        "n_pairs": int(len(sel)),
        "n_query_conformers": int(len(uq)),
        "n_library_conformers": int(len(ul)),
        "candidate_set": {
            "source": str(a.rescored),
            "n_comparable_non_self_pairs": int(len(cand)),
            "filter": "same_atom_set & ~is_self_match",
        },
        "delta_definition": (f"oracle({REFERENCE_ARM}, as_built) - "
                             f"oracle({BASELINE_ARM}, as_built), per channel; "
                             f"both arms at 25 steps"),
        "bins": {"r3_better": f"delta >= +{BETTER}", "tie": f"|delta| <= {TIE}",
                 "r2_better": f"delta <= -{BETTER}"},
        "within_bin_rule": (f"nearest-rank {PERCENTILES} percentiles of that "
                            f"cell's delta; deterministic, no seed"),
        "extremes": {t: int(k) for t, k in extremes.items()},
        "cells": {k: [int(i) for i in v] for k, v in cells.items()},
        "arms": arm_meta,
        "provenance": {"panel": str(a.panel), "rescored": str(a.rescored),
                       "mirror": str(a.mirror)},
        "note": ("bin proportions here are chosen, not measured -- this is a "
                 "stratified sample and no fraction computed over it estimates "
                 "a panel fraction"),
    }
    outp.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    log(f"[fixture] wrote {outp} ({outp.stat().st_size / 1024:.0f} KiB) "
        f"and {outp.with_suffix('.meta.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
