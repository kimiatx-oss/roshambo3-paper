"""Why do the two engines' top-100 lists disagree -- promotion or demotion?

Every prior T169 experiment is PAIR-level: it asks whether one engine finds a
better pose than the other for a given (query, library) pair. The question this
answers is RANKING-level and does not follow from those: when a molecule sits in
ROSHAMBO2's top-100 and not in ROSHAMBO3's, is that because

  * ROSHAMBO3 scored it WORSE  (demotion -- our optimizer did a worse job), or
  * ROSHAMBO3 scored it the same or better and something else overtook it
    (displacement -- our optimizer did a BETTER job on the molecules that
    passed it).

Those have opposite implications and the aggregate pair statistics cannot tell
them apart, because a pair-level win rate says nothing about which molecules
cross the top-100 boundary.

The comparator is `run2_fixed` -- ROSHAMBO2 with C1+C2+C3 -- so the fixes are
not part of what is being attributed. See the README in this directory.

Censoring, stated because it bounds the answer: an oracle stores only the
per-query top-1000, so a molecule that leaves ROSHAMBO3's top-1000 entirely has
no ROSHAMBO3 score here and is counted separately rather than assumed demoted.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from pathlib import Path

import numpy as np

INPUTS_DEFAULT = str(Path(__file__).resolve().parent.parent / "data" / "ranking-inputs.npz")

# The packaged input carries only what this analysis reads: per query, each
# engine's top-1000 indices and scores per channel. It is a repackaging of the
# two oracle directories named in data/provenance.json, not a re-measurement --
# the sha256 of every source file is recorded there.
_Z = None


def _open(inputs):
    global _Z
    if _Z is None:
        _Z = np.load(inputs)
    return _Z


def _load(engine, q, ch, inputs):
    z = _open(inputs)
    ki, ks = f"{engine}/{ch}/idx/{q}", f"{engine}/{ch}/score/{q}"
    if ki not in z:
        return None, None
    return z[ki], z[ks]


def fate(inputs, ch, k=100):
    qs = list(range(int(_open(inputs)["n_query"][0])))
    stayed = demoted = displaced = censored = 0
    drop, disp_gain, promo_gain = [], [], []
    traded, traded_total = 0, 0
    trade_shape_drop, trade_combo_gain = [], []
    for q in qs:
        a_i, a_s = _load("r2_fixed", q, ch, inputs)
        b_i, b_s = _load("roshambo3", q, ch, inputs)
        if a_i is None or b_i is None:
            continue
        A = dict(zip(a_i.tolist(), a_s.tolist()))
        B = dict(zip(b_i.tolist(), b_s.tolist()))
        a_top, b_top = set(a_i[:k].tolist()), set(b_i[:k].tolist())
        stayed += len(a_top & b_top)
        # Is a shape demotion the color/shape trade? Only askable on `shape`.
        Ac = Bc = None
        if ch == "shape":
            ac_i, ac_s = _load("r2_fixed", q, "combo", inputs)
            bc_i, bc_s = _load("roshambo3", q, "combo", inputs)
            Ac = dict(zip(ac_i.tolist(), ac_s.tolist()))
            Bc = dict(zip(bc_i.tolist(), bc_s.tolist()))
        for m in a_top - b_top:
            if m not in B:
                censored += 1
            elif B[m] < A[m]:
                demoted += 1
                drop.append(A[m] - B[m])
                if Ac is not None and m in Ac and m in Bc:
                    traded_total += 1
                    trade_shape_drop.append(A[m] - B[m])
                    trade_combo_gain.append(Bc[m] - Ac[m])
                    if Bc[m] > Ac[m]:
                        traded += 1
            else:
                displaced += 1
                disp_gain.append(B[m] - A[m])
        for m in b_top - a_top:
            if m in A:
                promo_gain.append(B[m] - A[m])
    left = demoted + displaced + censored
    out = {
        "channel": ch, "k": k, "n_query": len(qs),
        "stayed": stayed, "left": left,
        "demoted": demoted, "displaced": displaced, "censored": censored,
        "frac_demoted": demoted / left if left else None,
        "frac_displaced": displaced / left if left else None,
        "frac_censored": censored / left if left else None,
        "mean_drop_when_demoted": float(np.mean(drop)) if drop else None,
        "mean_gain_when_displaced": float(np.mean(disp_gain)) if disp_gain else None,
        "n_promoted_in": len(promo_gain),
        "mean_gain_on_promoted": float(np.mean(promo_gain)) if promo_gain else None,
    }
    if ch == "shape" and traded_total:
        out["shape_demotion_is_the_combo_trade"] = {
            "n_with_both_combo_scores": traded_total,
            "n_total_demoted": demoted,
            "note": "the rest fall outside one engine's top-1000 for combo",
            "frac_with_higher_combo_under_r3": traded / traded_total,
            "mean_shape_drop": float(np.mean(trade_shape_drop)),
            "mean_combo_gain": float(np.mean(trade_combo_gain)),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default=INPUTS_DEFAULT)
    ap.add_argument("--k", type=int, default=100)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "generated" / "ranking-discordance.json"))
    a = ap.parse_args()
    res = {"_meta": {"inputs": a.inputs, "k": a.k,
                     "question": "is a top-k discordance demotion or displacement"},
           "by_channel": {ch: fate(a.inputs, ch, a.k) for ch in ("combo", "shape")}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    for ch, r in res["by_channel"].items():
        print(f"{ch:<7} stayed {r['stayed']:>7,}  left {r['left']:>6,}  "
              f"demoted {r['frac_demoted']:.1%}  displaced {r['frac_displaced']:.1%}  "
              f"censored {r['frac_censored']:.1%}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
