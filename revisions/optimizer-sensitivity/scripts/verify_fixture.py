"""T169: re-score the committed iso-step fixture from its own bytes and assert.

This is the fixture's reason for existing.  It reads one 104 KiB file, needs no
GPU, no corpus, no external oracle directory and no network, and it re-derives
every score in it from the coordinates -- then checks each against the number
recorded when the fixture was built.  A future change that moves the oracle, the
pose convention, the feature numbering or the mixing rule fails here in seconds
instead of surviving until someone re-runs a 470 MB panel.

It re-derives rather than re-reads: the poses are reconstructed from the raw
20-column rows, the transforms rebuilt, the Tanimotos recomputed by
``roshambo3.reference.overlap``.  The recorded values are the expectation, not
the input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pose_rescore import Molecules, kernel_rotation_matrix, score_pose  # noqa: E402

CH = ("tanimoto_shape", "tanimoto_color", "tanimoto_combination")
#: A ROSHAMBO2 arm is re-scored on the very coordinates its recorded value used,
#: so only float64 rounding separates them.  A ROSHAMBO3 arm's recorded value
#: came from the same coordinates too -- the fixture stores both engines'
#: preparations -- so the same bound applies to both.
TOL = 1e-12
#: The engines report in float32; the round-trip gate the second experiment set.
REPORTED_TOL = 1e-4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    a = ap.parse_args()

    from roshambo3.reference import overlap as R

    f = np.load(a.fixture, allow_pickle=True)
    meta = json.loads(Path(a.fixture).with_suffix(".meta.json").read_text())
    pq = np.asarray(f["pair_query"], np.int64)
    pl = np.asarray(f["pair_library"], np.int64)
    n = len(pq)
    arms = sorted({k.split("/")[1] for k in f.files if k.startswith("pose/")})

    mols = {}
    for arm in arms:
        eng = meta["arms"][arm]["engine"]
        eng = "roshambo3" if eng == "roshambo3" else "roshambo2"
        if eng in mols:
            continue
        rmat = np.asarray(meta["arms"][arm]["interaction_matrix_r"], np.float64)
        pmat = np.asarray(meta["arms"][arm]["interaction_matrix_p"], np.float64)
        tag = "r3" if eng == "roshambo3" else "r2"
        mols[eng] = (
            Molecules(f[f"{tag}_q_coords"], f[f"{tag}_q_types"],
                      f[f"{tag}_q_n_real"],
                      f[f"{tag}_q_n_total"] if tag == "r2" else None,
                      rmat, pmat, R),
            Molecules(f[f"{tag}_l_coords"], f[f"{tag}_l_types"],
                      f[f"{tag}_l_n_real"],
                      f[f"{tag}_l_n_total"] if tag == "r2" else None,
                      rmat, pmat, R))

    COL = {"tanimoto_combination": 0, "tanimoto_shape": 1, "tanimoto_color": 2}
    failures = []
    worst_oracle, worst_reported, worst_identity = 0.0, 0.0, 0.0
    for arm in arms:
        rows = np.asarray(f[f"pose/{arm}"], np.float64)
        eng = "roshambo3" if meta["arms"][arm]["engine"] == "roshambo3" else "roshambo2"
        qm, lm = mols[eng]
        for k in range(n):
            q, t = rows[k, 9:13], rows[k, 13:16]
            q_rot = None if eng == "roshambo3" else R.quaternion_matrix(rows[k, 16:20])
            got = score_pose(R, qm, lm, int(pq[k]), int(pl[k]),
                             kernel_rotation_matrix(q), t, q_rot)
            for c in CH:
                key = f"oracle/{arm}/as_built/{c}"
                if key in f.files:
                    d = abs(got[c] - float(f[key][k]))
                    worst_oracle = max(worst_oracle, d)
                    if d > TOL:
                        failures.append(f"{arm} pair {k} {c}: recomputed "
                                        f"{got[c]:.12f} against recorded "
                                        f"{float(f[key][k]):.12f}")
                rep = float(f[f"reported/{arm}/{c}"][k])
                worst_reported = max(worst_reported, abs(rep - got[c]))
            worst_identity = max(worst_identity, abs(
                float(f[f"reported/{arm}/tanimoto_combination"][k])
                - 0.5 * (float(f[f"reported/{arm}/tanimoto_shape"][k])
                         + float(f[f"reported/{arm}/tanimoto_color"][k]))))
            if abs(rows[k, COL["tanimoto_shape"]] - got["tanimoto_shape"]) > REPORTED_TOL:
                failures.append(f"{arm} pair {k}: the pose does not reproduce "
                                f"the engine's own reported shape Tanimoto")

    print(f"fixture           {a.fixture}")
    print(f"pairs             {n}, arms {arms}")
    print(f"oracle recompute  max |recomputed - recorded| = {worst_oracle:.2e} "
          f"(tolerance {TOL:.0e})")
    print(f"round-trip gate   max |reported - oracle|     = {worst_reported:.2e} "
          f"(tolerance {REPORTED_TOL:.0e})")
    print(f"combo identity    max |combo - (s+c)/2|       = {worst_identity:.2e}")
    if failures:
        for x in failures[:20]:
            print("FAIL", x, file=sys.stderr)
        print(f"FAIL: {len(failures)} checks failed", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
