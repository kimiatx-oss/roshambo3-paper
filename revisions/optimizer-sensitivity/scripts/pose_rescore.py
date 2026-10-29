"""T169 follow-up: rescore both engines' final poses with one neutral oracle.

The first T169 experiment could not tell **search** from **scoring**, because
every Tanimoto in it was reported by the engine that also chose the pose.  This
script takes the final pose out of each arm, reconstructs the absolute
transform, and evaluates it with ``roshambo3.reference.overlap`` -- float64, in
physical units, sharing no code with either kernel, which is the whole point
under pitfall 5 ("C++ and CUDA agree because they share the typo").

Three questions, and they have different answers
------------------------------------------------
1. *Does each engine's reported score agree with the oracle's score of its own
   pose?*  A systematic disagreement there is a scoring defect and would be a
   bigger finding than any search difference.  This is also the **gate**: an
   arm whose pose does not round-trip against its own reported number has been
   reconstructed wrongly, and nothing downstream of it means anything.
2. *Does ROSHAMBO3's pose score better under the neutral oracle?*  That is
   search quality, measured without either engine's arithmetic in the loop.
3. *What did the pre-fix engine actually do, and what is the nearest rigid pose
   to it?*  Two different questions.  The C1 typo
   (``q[2]*q[2] * q[3]*q[3]`` for ``+``) leaves ``q`` non-unit while
   ``quaternion_to_rotation_matrix`` applies the **unit**-quaternion formula, so
   the matrix the kernel built is not a rotation.  ``as_built`` reproduces that
   matrix exactly, non-rigid and all; ``rigid`` renormalizes ``q`` first.  The
   gap between them is the score cost of C1, per pair.

Pose reconstruction, which is the one thing that must not be guessed
--------------------------------------------------------------------
* **ROSHAMBO3, field path.** ``START_QUAT`` is the identity -- checked here
  against the arm's own output, not taken from the docstring, because
  ``roshambo3.scores`` documents both behaviors in the same file.  The pose is
  ``b @ R(q).T + t``.
* **ROSHAMBO2.** The start-mode rotation is applied to the **query**
  (``start_mode_transform(molA_global, molA, qr, ...)``) and reported in columns
  16-19; the optimizer's ``(q, t)`` transforms the **library**.  So the scored
  configuration is ``R(q_start) a`` against ``b @ R(q_fit).T + t``, and every
  arm here reports a non-identity start quaternion.

Both channels are scored.  The oracle reproduces ROSHAMBO2's color term as
written -- ``exp(-r/2 d^2) p^2 r^-1.5 (pi/2)^1.5``, which is
``cuda_functions.cu``'s ``p*p*exp(-a*a*d2/(a+a))*(PI/(2a))^1.5`` -- and both
engines mix as ``(1-m) T_shape + m T_color`` at ``m = 0.5``, so combo is a
faithful comparison and not an approximation.  The two engines number the six
feature families differently (ROSHAMBO2 Donor=1..Hydrophobe=6, ROSHAMBO3
Hydrophobe=1..NegIonizable=6 since T106); each arm is therefore scored under its
own numbering with its own interaction matrix, both recorded by the arm scripts
and checked here to be the same canonical matrix.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

MIXING = 0.5


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def kernel_rotation_matrix(q) -> np.ndarray:
    """``quaternion_to_rotation_matrix`` exactly as ROSHAMBO2's kernel writes it.

    The unit-quaternion formula, applied to whatever ``q`` it is handed and with
    **no normalization**.  For a unit ``q`` this is a rotation; for the pre-fix
    build's ``q`` it is not, and reproducing that is the point -- see
    ``cuda_functions.cu:54``.  ``reference.overlap.quaternion_matrix`` normalizes
    first and is therefore the *rigid* reconstruction, not this one.
    """
    w, x, y, z = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


class Molecules:
    """One engine's prepared conformers, with the oracle's self-overlaps cached."""

    def __init__(self, coords, types, n_real, n_total, rmat, pmat, R):
        self.R = R
        self.rmat, self.pmat = rmat, pmat
        self.shape, self.color, self.ctype = [], [], []
        for i in range(coords.shape[0]):
            nr = int(n_real[i])
            self.shape.append(coords[i, :nr, :3].astype(np.float64))
            if n_total is None:                      # roshambo3: type plane
                sel = np.flatnonzero(types[i] != 0)
            else:                                    # roshambo2: [n_real, n_total)
                sel = np.arange(nr, int(n_total[i]))
            self.color.append(coords[i, sel, :3].astype(np.float64))
            self.ctype.append(np.asarray(types[i])[sel].astype(np.int64))
        self._vaa = [None] * len(self.shape)
        self._caa = [None] * len(self.shape)

    def self_shape(self, i: int) -> float:
        if self._vaa[i] is None:
            self._vaa[i] = self.R.self_overlap(self.shape[i])
        return self._vaa[i]

    def self_color(self, i: int) -> float:
        if self._caa[i] is None:
            self._caa[i] = self.R.color_overlap(
                self.color[i], self.ctype[i], self.color[i], self.ctype[i],
                self.rmat, self.pmat)
        return self._caa[i]


def score_pose(R, qm: Molecules, lm: Molecules, qi: int, li: int,
               M: np.ndarray, t: np.ndarray, q_rot: np.ndarray | None) -> dict:
    """Oracle score of ``lm[li]`` transformed by ``(M, t)`` onto ``qm[qi]``.

    ``q_rot`` is the start-mode rotation applied to the QUERY, or None for an
    identity start.  ``M`` is a 3x3 matrix rather than a quaternion so the
    caller can hand over the pre-fix kernel's non-rigid one.
    """
    a = qm.shape[qi]
    ac = qm.color[qi]
    if q_rot is not None:
        a = a @ q_rot.T
        ac = ac @ q_rot.T
    b = lm.shape[li] @ M.T + t
    v_ab = R.pair_overlap(a, b)
    ts = R.tanimoto(v_ab, qm.self_shape(qi), lm.self_shape(li))
    bc = lm.color[li] @ M.T + t
    c_ab = R.color_overlap(ac, qm.ctype[qi], bc, lm.ctype[li],
                           qm.rmat, qm.pmat)
    tc = R.tanimoto(c_ab, qm.self_color(qi), lm.self_color(li))
    return {"tanimoto_shape": ts, "tanimoto_color": tc,
            "tanimoto_combination": (1 - MIXING) * ts + MIXING * tc,
            "overlap_volume": v_ab, "overlap_color": c_ab}


def paired_stats(d: np.ndarray, cluster: np.ndarray | None = None) -> dict:
    """Mean, spread and sign of a paired difference.

    ``se`` is the ordinary paired standard error; ``se_by_query`` clusters on the
    query molecule, because pairs sharing a query are not independent draws and
    the ordinary one would be too small.
    """
    d = np.asarray(d, np.float64)
    n = int(d.size)
    out = {"n": n, "mean": float(d.mean()), "median": float(np.median(d)),
           "sd": float(d.std(ddof=1)) if n > 1 else 0.0,
           "se": float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0,
           "q10": float(np.quantile(d, 0.10)), "q25": float(np.quantile(d, 0.25)),
           "q75": float(np.quantile(d, 0.75)), "q90": float(np.quantile(d, 0.90)),
           "min": float(d.min()), "max": float(d.max()),
           "frac_positive": float((d > 0).mean()),
           "frac_negative": float((d < 0).mean()),
           "mean_abs": float(np.abs(d).mean())}
    if cluster is not None and n > 1:
        u = np.unique(cluster)
        dev = d - d.mean()
        s = np.array([dev[cluster == g].sum() for g in u])
        g = len(u)
        if g > 1:
            var = (s ** 2).sum() * g / ((g - 1) * n * n)
            out["se_by_query"] = float(np.sqrt(max(var, 0.0)))
            out["n_query_clusters"] = int(g)
    return out


def residual_stats(d: np.ndarray) -> dict:
    d = np.abs(np.asarray(d, np.float64))
    return {"n": int(d.size), "max": float(d.max()),
            "median": float(np.median(d)), "p99": float(np.quantile(d, 0.99)),
            "mean": float(d.mean())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--arm", action="append", default=[],
                    help="name=path/to/arm.npy, repeatable")
    ap.add_argument("--reference-arm", default="roshambo3")
    ap.add_argument("--gate", type=float, default=1e-4,
                    help="round-trip residual a float32 arm must beat")
    ap.add_argument("--r2-oracle", default="",
                    help="the T169 ROSHAMBO2 arm directory this arm stands "
                         "for, for the molecule-level consistency check")
    ap.add_argument("--r3-oracle", default="",
                    help="the T169 ROSHAMBO3 oracle directory")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-record", default="",
                    help="append a JSONL run record here")
    ap.add_argument("--grade", default="advisory")
    ap.add_argument("--grade-reason", default="")
    a = ap.parse_args()

    from roshambo3.pharmacophore import RDKitPharmacophoreGenerator
    from roshambo3.reference import overlap as R

    f = np.load(a.panel, allow_pickle=True)
    pq = np.asarray(f["pair_query"], np.int64)
    pl = np.asarray(f["pair_library"], np.int64)
    stratum = np.asarray([str(s) for s in f["pair_stratum"]])
    qmol = np.asarray(f["pair_query_molecule"], np.int64)
    qkeys = [str(k) for k in f["query_keys"]]
    lkeys = [str(k) for k in f["library_keys"]]
    same_atoms = (np.asarray(f["q_same_atom_set"])[pq]
                  & np.asarray(f["l_same_atom_set"])[pl])
    is_self = np.array([qkeys[i] == lkeys[j] for i, j in zip(pq, pl)])
    log(f"[rescore] {len(pq)} pairs, {int(same_atoms.sum())} with a heavy-atom "
        f"set both engines agree on, {int(is_self.sum())} exact self-matches")

    canonical_r = np.asarray(RDKitPharmacophoreGenerator().interaction_matrix_r,
                             np.float64)
    canonical_p = np.asarray(RDKitPharmacophoreGenerator().interaction_matrix_p,
                             np.float64)

    arms: dict[str, dict] = {}
    for spec in a.arm:
        name, _, path = spec.partition("=")
        side = json.loads(Path(path).with_suffix(".json").read_text())
        rows = np.load(path).astype(np.float64)
        rmat = np.asarray(side["interaction_matrix_r"], np.float64)
        pmat = np.asarray(side["interaction_matrix_p"], np.float64)
        if not (np.array_equal(rmat, canonical_r)
                and np.array_equal(pmat, canonical_p)):
            raise SystemExit(
                f"arm {name} used a non-canonical interaction matrix; the "
                f"cross-engine color comparison assumes both engines use the "
                f"same one under their own numbering")
        arms[name] = {"rows": rows, "sidecar": side,
                      "engine": "roshambo3" if side["engine"] == "roshambo3"
                                else "roshambo2"}
        log(f"[rescore] arm {name}: {rows.shape} from {side['engine']}")

    mols = {
        "roshambo2": (Molecules(f["r2_q_coords"], f["r2_q_types"],
                                f["r2_q_n_real"], f["r2_q_n_total"],
                                canonical_r, canonical_p, R),
                      Molecules(f["r2_l_coords"], f["r2_l_types"],
                                f["r2_l_n_real"], f["r2_l_n_total"],
                                canonical_r, canonical_p, R)),
        "roshambo3": (Molecules(f["r3_q_coords"], f["r3_q_types"],
                                f["r3_q_n_real"], None,
                                canonical_r, canonical_p, R),
                      Molecules(f["r3_l_coords"], f["r3_l_types"],
                                f["r3_l_n_real"], None,
                                canonical_r, canonical_p, R)),
    }

    CH = ("tanimoto_shape", "tanimoto_color", "tanimoto_combination")
    COL = {"tanimoto_combination": 0, "tanimoto_shape": 1, "tanimoto_color": 2}

    # --- oracle rescoring --------------------------------------------------
    oracle: dict[str, dict[str, np.ndarray]] = {}
    rotation: dict[str, dict] = {}
    for name, arm in arms.items():
        rows = arm["rows"]
        qm, lm = mols[arm["engine"]]
        variants = ("as_built", "rigid") if arm["engine"] == "roshambo2" else ("as_built",)
        for v in variants:
            oracle[f"{name}/{v}"] = {c: np.zeros(len(pq)) for c in CH}
        qn = np.linalg.norm(rows[:, 9:13], axis=1)
        det = np.zeros(len(pq))
        orth = np.zeros(len(pq))
        smax = np.zeros(len(pq))
        smin = np.zeros(len(pq))
        if arm["engine"] == "roshambo3":
            sq = np.round(rows[:, 16:20], 6)
            if not np.array_equal(np.unique(sq, axis=0), np.array([[1., 0., 0., 0.]])):
                raise SystemExit(
                    f"arm {name} reports a non-identity START_QUAT; the field "
                    f"path's pose reconstruction here assumes the start-mode "
                    f"rotation is folded in, and it is not")
        for k in range(len(pq)):
            qi, li = int(pq[k]), int(pl[k])
            q = rows[k, 9:13]
            t = rows[k, 13:16]
            q_rot = (None if arm["engine"] == "roshambo3"
                     else R.quaternion_matrix(rows[k, 16:20]))
            M = kernel_rotation_matrix(q)
            det[k] = np.linalg.det(M)
            orth[k] = np.abs(M.T @ M - np.eye(3)).max()
            s = np.linalg.svd(M, compute_uv=False)
            smax[k], smin[k] = s.max(), s.min()
            o = score_pose(R, qm, lm, qi, li, M, t, q_rot)
            for c in CH:
                oracle[f"{name}/as_built"][c][k] = o[c]
            if "rigid" in variants:
                o2 = score_pose(R, qm, lm, qi, li, R.quaternion_matrix(q), t, q_rot)
                for c in CH:
                    oracle[f"{name}/rigid"][c][k] = o2[c]
        rotation[name] = {
            "quaternion_norm": {"min": float(qn.min()), "max": float(qn.max()),
                                "median": float(np.median(qn)),
                                "max_abs_error": float(np.abs(qn - 1).max()),
                                "p99_abs_error": float(np.quantile(np.abs(qn - 1), 0.99))},
            "det": {"min": float(det.min()), "max": float(det.max()),
                    "median": float(np.median(det)),
                    "max_abs_error": float(np.abs(det - 1).max())},
            "orthogonality_max_abs_MtM_minus_I": {
                "max": float(orth.max()), "median": float(np.median(orth)),
                "p99": float(np.quantile(orth, 0.99))},
            "singular_values": {"max_stretch": float(smax.max()),
                                "min_compression": float(smin.min()),
                                "median_max_stretch": float(np.median(smax)),
                                "p99_max_stretch": float(np.quantile(smax, 0.99))},
            # Two thresholds on purpose: 1e-6 is inside float32 rounding of a
            # unit quaternion and catches nothing but that, 1e-4 is a matrix
            # that is really not a rotation.
            "n_pairs_not_a_rotation_1e-6": int((orth > 1e-6).sum()),
            "n_pairs_not_a_rotation_1e-4": int((orth > 1e-4).sum()),
        }
        log(f"[rescore] {name}: max ||q||-1 {np.abs(qn - 1).max():.3e}, "
            f"max |det-1| {np.abs(det - 1).max():.3e}, "
            f"max stretch {smax.max():.4f}")

    # --- the gate: does each arm's pose reproduce its own reported score? ---
    gate: dict[str, dict] = {}
    gate_ok = True
    for name, arm in arms.items():
        rows = arm["rows"]
        key = f"{name}/as_built"
        cell = {}
        for c in CH:
            d = rows[:, COL[c]] - oracle[key][c]
            cell[c] = residual_stats(d)
        cell["reported_combo_minus_half_sum"] = residual_stats(
            rows[:, 0] - 0.5 * (rows[:, 1] + rows[:, 2]))
        cell["passes"] = bool(cell["tanimoto_shape"]["max"] <= a.gate)
        gate_ok &= cell["passes"]
        gate[name] = cell
        log(f"[gate] {name}: |reported - oracle| shape max "
            f"{cell['tanimoto_shape']['max']:.2e}, color max "
            f"{cell['tanimoto_color']['max']:.2e} -> "
            f"{'PASS' if cell['passes'] else 'FAIL'}")
    if not gate_ok:
        raise SystemExit("the round-trip gate failed; the pose reconstruction "
                         "is wrong and nothing below it may be reported")

    # --- the C1 cost: what the non-rigid matrix cost, per pair -------------
    c1 = {}
    for name, arm in arms.items():
        if arm["engine"] != "roshambo2":
            continue
        cell = {}
        for c in CH:
            d = (oracle[f"{name}/rigid"][c] - oracle[f"{name}/as_built"][c])
            cell[c] = paired_stats(d, qmol)
        c1[name] = cell

    # --- the cross-engine comparison, under the neutral oracle -------------
    ref = f"{a.reference_arm}/as_built"
    ok = same_atoms
    cross = {}
    for name, arm in arms.items():
        if name == a.reference_arm:
            continue
        for v in (("as_built", "rigid") if arm["engine"] == "roshambo2"
                  else ("as_built",)):
            key = f"{name}/{v}"
            cell = {"n_comparable_pairs": int(ok.sum()), "by_channel": {}}
            for c in CH:
                d = oracle[ref][c][ok] - oracle[key][c][ok]
                s = paired_stats(d, qmol[ok])
                s["by_stratum"] = {
                    st: paired_stats(d[stratum[ok] == st])
                    for st in sorted(set(stratum[ok].tolist()))}
                # search vs scoring: the reported difference splits exactly
                rep = (arms[a.reference_arm]["rows"][ok, COL[c]]
                       - arms[name]["rows"][ok, COL[c]])
                resid = ((arms[a.reference_arm]["rows"][ok, COL[c]]
                          - oracle[ref][c][ok])
                         - (arms[name]["rows"][ok, COL[c]] - oracle[key][c][ok]))
                s["decomposition"] = {
                    "reported_difference": paired_stats(rep, qmol[ok]),
                    "search_component_oracle_difference": paired_stats(d, qmol[ok]),
                    "scoring_component_residual_difference": residual_stats(resid),
                    "search_share_of_mean": (float(d.mean() / rep.mean())
                                             if rep.mean() != 0 else None),
                    "max_abs_identity_error": float(
                        np.abs(rep - (d + resid)).max()),
                }
                cell["by_channel"][c] = s
            cross[f"{a.reference_arm}_minus_{name}_{v}"] = cell

    # --- controls ----------------------------------------------------------
    # The engines' inputs differ by the corpus's int16 quantization.  Bound its
    # effect directly: rescore the reference arm's own pose against the OTHER
    # engine's coordinate arrays and report the shift.
    qm2, lm2 = mols["roshambo2"]
    ref_rows = arms[a.reference_arm]["rows"]
    swap = {c: np.full(len(pq), np.nan) for c in CH}
    for k in np.flatnonzero(same_atoms):
        o = score_pose(R, qm2, lm2, int(pq[k]), int(pl[k]),
                       kernel_rotation_matrix(ref_rows[k, 9:13]),
                       ref_rows[k, 13:16], None)
        for c in CH:
            swap[c][k] = o[c]
    quantization = {c: residual_stats(
        swap[c][same_atoms] - oracle[ref][c][same_atoms]) for c in CH}

    # Self-overlaps under the oracle, per engine: the denominators the Tanimoto
    # is built on, and the other place a coordinate difference would show.
    vaa2 = np.array([qm2.self_shape(i) for i in range(len(qkeys))])
    qm3 = mols["roshambo3"][0]
    vaa3 = np.array([qm3.self_shape(i) for i in range(len(qkeys))])
    keep_q = np.asarray(f["q_same_atom_set"])
    self_overlap_control = residual_stats(
        (vaa3[keep_q] - vaa2[keep_q]) / vaa2[keep_q])

    # The self-match: the one pair whose exact optimum is 1.0.
    self_match = {}
    for name in arms:
        key = f"{name}/as_built"
        cell = {}
        for c in CH:
            v = oracle[key][c][is_self]
            cell[c] = {"n": int(v.size), "median": float(np.median(v)),
                       "min": float(v.min()), "max": float(v.max()),
                       "mean": float(v.mean()),
                       "frac_at_1_to_1e-6": float((v > 1 - 1e-6).mean())}
        cell["reported_shape_median"] = float(
            np.median(arms[name]["rows"][is_self, 1]))
        self_match[name] = cell

    # Does each arm reproduce the T169 oracle it stands for?  The oracles are
    # MOLECULE-level ensemble maxima (pitfall 9) and a panel row is one
    # conformer pair, so the only exact relation is an inequality: the
    # molecule's maximum cannot be below any single pair inside it.  A
    # systematic violation would mean this arm is not the configuration the
    # oracle ran, which is the failure worth catching.
    consistency = {}
    for name, oracle_dir, col in (("r2_fixed", a.r2_oracle, "full_combo"),
                                  (a.reference_arm, a.r3_oracle, "topk_combo")):
        if not oracle_dir or name not in arms:
            continue
        cands = np.load(Path(oracle_dir) / "candidates.npy").astype(np.int64)
        lib_mol = np.array([int(k.split("_")[0]) for k in lkeys], np.int64)
        slack, n_seen, n_viol = [], 0, 0
        for qm_id in np.unique(qmol):
            p = Path(oracle_dir) / f"q_{int(qm_id)}.npz"
            if not p.exists():
                continue
            z = np.load(p)
            if col == "full_combo" and "full_combo" in z:
                # The whole 75,292-molecule reduced vector.
                value = {int(cands[i]): float(v)
                         for i, v in enumerate(np.asarray(z["full_combo"]))}
            else:
                # Only the top-1000 survives on this oracle, and its values are
                # indexed by `topk_combo_idx` -- pairing them with `cands` by
                # POSITION instead would silently score every hit against the
                # wrong molecule.
                idx = np.asarray(z["topk_combo_idx"], np.int64)
                value = {int(cands[i]): float(v)
                         for i, v in zip(idx, np.asarray(z["topk_combo"]))}
            for k in np.flatnonzero(qmol == qm_id):
                got = value.get(int(lib_mol[pl[k]]))
                if got is None:
                    continue
                n_seen += 1
                s = got - float(arms[name]["rows"][k, 0])
                slack.append(s)
                n_viol += int(s < -1e-5)
        if n_seen:
            sl = np.asarray(slack)
            consistency[name] = {
                "oracle": str(oracle_dir), "n_checked": n_seen,
                "n_violations_beyond_1e-5": n_viol,
                "molecule_max_minus_pair_combo": {
                    "min": float(sl.min()), "median": float(np.median(sl)),
                    "frac_attained_1e-5": float((np.abs(sl) < 1e-5).mean())},
            }
            log(f"[consistency] {name}: {n_viol}/{n_seen} pairs exceed their "
                f"own molecule's oracle maximum by more than 1e-5")

    record = {
        "panel": str(a.panel),
        "n_pairs": int(len(pq)),
        "n_comparable_pairs": int(same_atoms.sum()),
        "excluded_pairs_atom_set_differs": int((~same_atoms).sum()),
        "reference_arm": a.reference_arm,
        "gate_threshold": a.gate,
        "arms": {n: arms[n]["sidecar"] for n in arms},
        "round_trip_gate": gate,
        "rotation_statistics": rotation,
        "c1_cost_rigid_minus_as_built": c1,
        "cross_engine_under_the_oracle": cross,
        "controls": {
            "reproduces_the_t169_oracles": consistency,
            "quantization_effect_on_reference_arm_score": quantization,
            "relative_self_overlap_difference_r3_vs_r2": self_overlap_control,
        },
        "self_match": self_match,
        "per_stratum_pairs": {st: int((stratum == st).sum())
                              for st in sorted(set(stratum.tolist()))},
    }
    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(record, indent=2) + "\n")

    if a.run_record:
        import datetime
        import platform
        import subprocess

        def smi(query: str) -> list[str]:
            try:
                return subprocess.run(
                    ["nvidia-smi", f"--query-{query}", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=30
                ).stdout.strip().splitlines()
            except Exception as e:                            # noqa: BLE001
                return [f"unavailable: {e}"]
        headline = {}
        for k, cell in cross.items():
            headline[k] = {c: {"mean": s["mean"], "se_by_query": s.get("se_by_query"),
                               "median": s["median"],
                               "frac_reference_better": s["frac_positive"],
                               "scoring_component_max_abs":
                                   s["decomposition"]["scoring_component_residual_difference"]["max"]}
                           for c, s in cell["by_channel"].items()}
        line = {
            "ticket": "T169",
            "kind": "pose rescoring under the float64 oracle "
                    "(search versus scoring)",
            # Correctness run; deterministic statistics, no GPU lock, no timing quoted.
            "grade": a.grade,
            "grade_reason": a.grade_reason,
            "timestamp_utc": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            "host": platform.node(),
            "gpu": smi("gpu=name,driver_version"),
            "machine_state": {
                "compute_apps": smi("compute-apps=pid,process_name,used_gpu_memory"),
                "utilization": smi("gpu=utilization.gpu,memory.used,power.draw"),
                "lock_held": False,
                "note": "Correctness run; deterministic statistics, no GPU lock, "
                        "no timing quoted.",
            },
            "panel": {"pairs": int(len(pq)),
                      "comparable_pairs": int(same_atoms.sum()),
                      "query_conformers": len(qkeys),
                      "library_conformers": len(lkeys),
                      "file": str(a.panel)},
            "arms": {n: arms[n]["sidecar"].get("config") for n in arms},
            "round_trip_gate_max_abs_shape": {
                n: gate[n]["tanimoto_shape"]["max"] for n in gate},
            "headline": headline,
            "controls": record["controls"],
            "scripts": ["tickets/T169/pose_panel.py",
                        "tickets/T169/pose_arm_roshambo2.py",
                        "tickets/T169/pose_arm_roshambo3.py",
                        "tickets/T169/pose_rescore.py"],
            "artifact": str(outp),
        }
        with open(a.run_record, "a") as fh:
            fh.write(json.dumps(line) + "\n")
        log(f"[rescore] appended a run record to {a.run_record}")

    # Per-pair table, so the analysis can be redone without re-running the oracle.
    tab = {"pair_query": pq, "pair_library": pl, "pair_stratum": stratum,
           "pair_query_molecule": qmol, "same_atom_set": same_atoms,
           "is_self_match": is_self}
    for name, arm in arms.items():
        for c in CH:
            tab[f"reported/{name}/{c}"] = arm["rows"][:, COL[c]]
        tab[f"quaternion_norm/{name}"] = np.linalg.norm(arm["rows"][:, 9:13], axis=1)
    for key, chans in oracle.items():
        for c, v in chans.items():
            tab[f"oracle/{key}/{c}"] = v
    for c in CH:
        tab[f"oracle/{a.reference_arm}_pose_on_roshambo2_coords/{c}"] = swap[c]
    np.savez(outp.with_suffix(".pairs.npz"), **tab)
    log(f"[rescore] wrote {outp} and {outp.with_suffix('.pairs.npz')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
