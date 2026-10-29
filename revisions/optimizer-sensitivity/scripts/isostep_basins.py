"""T169 third experiment: why the two engines disagree, pair by pair.

The second experiment established *that* the disagreement is search rather than
scoring, and that at matched step count the shape channel is a coin flip with a
10.8% left tail.  This script asks what produces the tail.  It runs on the
committed fixture and nothing else.

The mechanism question, made decidable
--------------------------------------
"Same basin" and "different basin" are only meaningful if a basin is defined
operationally, so it is defined here as **the attractor of local ascent**: from
each engine's final pose, run one Powell maximization of the same mixed
objective the engines optimize, with no restarts, and see where it stops.  Two
poses are in the same basin when their refinements land on the same
configuration -- measured as the RMSD between the two refined *placements* of
the library's heavy atoms, which is frame-free and does not need rotation and
translation to be compared separately.

That definition buys an exact decomposition.  Writing ``G`` for the float64
global optimum of the mixed objective, ``L_E`` for where engine ``E``'s pose
refines to, and ``S_E`` for what engine ``E`` actually scored,

    G - S_E  =  (G - L_E)   +   (L_E - S_E)
                 breadth          depth

-- breadth is what choosing the wrong basin cost, depth is what stopping early
inside the right one cost -- and the cross-engine difference decomposes term by
term:

    S_R3 - S_R2  =  (breadth_R2 - breadth_R3)  +  (depth_R2 - depth_R3)

So "is ROSHAMBO3's tail a start-set problem or a step-budget problem" is a
question with an arithmetic answer, per pair, rather than an impression.

D019 is why the depth term cannot be dismissed as a fair fight.  ``steps`` and
``lr_t`` are one knob there, so 25 ROSHAMBO3 steps at the derived ``lr_t=0.4``
and 25 ROSHAMBO2 steps at its free ``lr_t=0.1`` are the same *count* and not the
same *travel*.  The mirror arm (ROSHAMBO3 at 10 steps, run alongside this) is
what bounds that confound; it does not remove it.

Everything is computed on the ROSHAMBO2 coordinate arrays, including
ROSHAMBO3's pose, for the reason ``pose_global_optimum.py`` gives: one reference
must serve both arms, the two prepared frames coincide to 5.0e-4 A, and the
effect of that difference on a Tanimoto was measured at 1.1e-4 -- two orders
below anything read here.  The reconstruction is checked, not assumed: ROSHAMBO2
reports its start rotation applied to the *query*, so its pose is folded into the
query-unrotated frame and the fold is verified to leave the score unchanged.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

MIXING = 0.5
CH = ("tanimoto_shape", "tanimoto_color", "tanimoto_combination")
OBJECTIVES = ("shape", "color", "combination")
#: Two refined placements closer than this are called the same basin.  0.10 A is
#: an order below the corpus's own atom-placement scale and two orders below the
#: inter-basin distances actually observed (reported in the output, so the
#: threshold can be checked against the gap rather than trusted).
SAME_BASIN_RMSD_A = 0.10
#: Two optima whose scores agree this closely are equivalent for ranking, even
#: if their placements differ -- a near-symmetric molecule has genuinely
#: distinct poses of equal worth and calling that a "different basin" loss
#: would be wrong.
EQUIVALENT_SCORE = 1e-4

_F: dict = {}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def _init(fixture_path: str):
    """Per-worker load of the fixture into plain float64 arrays."""
    f = np.load(fixture_path, allow_pickle=True)
    d = {}
    for side in ("q", "l"):
        co = f[f"r2_{side}_coords"]
        nr = f[f"r2_{side}_n_real"]
        nt = f[f"r2_{side}_n_total"]
        ty = f[f"r2_{side}_types"]
        d[side] = [co[i, : int(nr[i]), :3].astype(np.float64)
                   for i in range(co.shape[0])]
        d[side + "c"] = [co[i, int(nr[i]): int(nt[i]), :3].astype(np.float64)
                         for i in range(co.shape[0])]
        d[side + "t"] = [ty[i, int(nr[i]): int(nt[i])].astype(np.int64)
                         for i in range(co.shape[0])]
    _F.clear()
    _F.update(d)


def kernel_rotation_matrix(q) -> np.ndarray:
    """ROSHAMBO2's ``quaternion_to_rotation_matrix``, no normalization.

    Transcribed from ``pose_rescore.py``, which is where it was validated
    against every arm's own reported score.
    """
    w, x, y, z = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def color_overlap_fast(a, at, b, bt, R):
    """``reference.overlap.color_overlap`` for the canonical interaction matrix.

    Same accelerator ``pose_global_optimum.py`` uses and checks; the check is
    re-run here rather than inherited.
    """
    if a.shape[0] == 0 or b.shape[0] == 0:
        return 0.0
    same = at[:, None] == bt[None, :]
    if not same.any():
        return 0.0
    d2 = ((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)
    return float(R.COLOR_PREFACTOR * np.exp(-0.5 * d2)[same].sum())


def check_fast_color(R) -> float:
    rng = np.random.default_rng(0)
    rmat, pmat = np.ones((7, 7)), np.zeros((7, 7))
    for i in range(1, 7):
        pmat[i, i] = 1.0
    worst = 0.0
    for _ in range(20):
        na, nb = int(rng.integers(1, 20)), int(rng.integers(1, 20))
        a, b = rng.normal(size=(na, 3)) * 3, rng.normal(size=(nb, 3)) * 3
        at, bt = rng.integers(1, 7, na), rng.integers(1, 7, nb)
        slow = R.color_overlap(a, at, b, bt, rmat, pmat)
        fast = color_overlap_fast(a, at, b, bt, R)
        worst = max(worst, abs(slow - fast) / max(abs(slow), abs(fast), 1e-30))
    return worst


def _terms(qi: int, li: int, R):
    a, ac, at = _F["q"][qi], _F["qc"][qi], _F["qt"][qi]
    b, bc, bt = _F["l"][li], _F["lc"][li], _F["lt"][li]
    v_aa, v_bb = R.self_overlap(a), R.self_overlap(b)
    c_aa = color_overlap_fast(ac, at, ac, at, R)
    c_bb = color_overlap_fast(bc, bt, bc, bt, R)
    return a, ac, at, b, bc, bt, v_aa, v_bb, c_aa, c_bb


def _scorer(qi: int, li: int, R):
    """``(M, t) -> the three Tanimotos``, on the query-unrotated frame."""
    a, ac, at, b, bc, bt, v_aa, v_bb, c_aa, c_bb = _terms(qi, li, R)

    def score(M, t):
        ts = R.tanimoto(R.pair_overlap(a, b @ M.T + t), v_aa, v_bb)
        tc = R.tanimoto(color_overlap_fast(ac, at, bc @ M.T + t, bt, R),
                        c_aa, c_bb)
        return {"tanimoto_shape": ts, "tanimoto_color": tc,
                "tanimoto_combination": (1 - MIXING) * ts + MIXING * tc}
    return score


def _neg_combo(qi: int, li: int, R):
    a, ac, at, b, bc, bt, v_aa, v_bb, c_aa, c_bb = _terms(qi, li, R)

    def neg(x):
        M = R.quaternion_matrix(x[:4])
        ts = R.tanimoto(R.pair_overlap(a, b @ M.T + x[4:]), v_aa, v_bb)
        tc = R.tanimoto(color_overlap_fast(ac, at, bc @ M.T + x[4:], bt, R),
                        c_aa, c_bb)
        return -((1 - MIXING) * ts + MIXING * tc)
    return neg


def _neg_shape(qi: int, li: int, R):
    a, _, _, b, _, _, v_aa, v_bb, _, _ = _terms(qi, li, R)

    def neg(x):
        M = R.quaternion_matrix(x[:4])
        return -R.tanimoto(R.pair_overlap(a, b @ M.T + x[4:]), v_aa, v_bb)
    return neg


def _powell(neg, x0):
    from scipy.optimize import minimize
    return minimize(neg, x0, method="Powell",
                    options={"xtol": 1e-10, "ftol": 1e-12, "maxiter": 40000})


def _global(args):
    """Global optimum of one objective for one pair, pose included."""
    qi, li, restarts, objective = args
    from roshambo3.reference import overlap as R
    neg = _neg_combo(qi, li, R) if objective == "combination" else _neg_shape(qi, li, R)
    rng = np.random.default_rng(0)
    seeds = [np.concatenate([R._axis_angle_quat(*s), np.zeros(3)])
             for s in R._CANONICAL_STARTS]
    while len(seeds) < restarts:
        q = rng.normal(size=4)
        seeds.append(np.concatenate([q / np.linalg.norm(q),
                                     rng.normal(scale=1.5, size=3)]))
    best_x, best_f = None, np.inf
    for x0 in seeds[:max(restarts, len(R._CANONICAL_STARTS))]:
        r = _powell(neg, x0)
        if r.fun < best_f:
            best_f, best_x = float(r.fun), r.x.copy()
    q = best_x[:4] / np.linalg.norm(best_x[:4])
    return -best_f, q, best_x[4:]


def _refine(args):
    """Local ascent from an engine's own pose: where does its basin lead?

    Powell is restarted from its own output until it stops improving, because a
    single Powell run can stall short of the local optimum and that stall would
    be indistinguishable from the engine's own under-convergence -- which is the
    exact quantity this is supposed to measure.  No new seeds are introduced, so
    this cannot cross into another basin.
    """
    qi, li, q0, t0 = args
    from roshambo3.reference import overlap as R
    neg = _neg_combo(qi, li, R)
    x = np.concatenate([np.asarray(q0, float), np.asarray(t0, float)])
    prev = np.inf
    for _ in range(6):
        r = _powell(neg, x)
        x = r.x
        if prev - float(r.fun) <= 1e-12:
            break
        prev = float(r.fun)
    q = x[:4] / np.linalg.norm(x[:4])
    return -float(r.fun), q, x[4:]


def geodesic_angle_deg(ra: np.ndarray, rb: np.ndarray) -> float:
    c = (np.trace(ra.T @ rb) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def placement_rmsd(b: np.ndarray, m1, t1, m2, t2) -> float:
    d = (b @ np.asarray(m1).T + t1) - (b @ np.asarray(m2).T + t2)
    return float(np.sqrt((d * d).sum(1).mean()))


def gyration(x: np.ndarray) -> tuple[float, float]:
    """Radius of gyration and the anisotropy ``l1/l3`` of the gyration tensor."""
    c = x - x.mean(0)
    ev = np.linalg.eigvalsh(c.T @ c / len(c))[::-1]
    return float(np.sqrt(ev.sum())), float(ev[0] / max(ev[2], 1e-12))


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return float("nan")
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    den = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / den) if den else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--restarts", type=int, default=256)
    ap.add_argument("--convergence-pairs", type=int, default=16)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--reference-arm", default="roshambo3")
    ap.add_argument("--baseline-arm", default="r2_fixed_steps25")
    a = ap.parse_args()

    from roshambo3.reference import overlap as R

    f = np.load(a.fixture, allow_pickle=True)
    meta = json.loads(Path(a.fixture).with_suffix(".meta.json").read_text())
    pq = np.asarray(f["pair_query"], np.int64)
    pl = np.asarray(f["pair_library"], np.int64)
    n = len(pq)
    arms = sorted({k.split("/")[1] for k in f.files if k.startswith("pose/")})
    log(f"[basins] {n} pairs, arms {arms}")

    fast_err = check_fast_color(R)
    log(f"[basins] color accelerator vs the oracle's own loop: {fast_err:.2e}")
    if fast_err > 1e-12:
        raise SystemExit("the color accelerator disagrees with the oracle")

    _init(a.fixture)

    # --- pose reconstruction, folded into the query-unrotated frame --------
    # ROSHAMBO2 scores R(q_start) a against b R(q_fit)^T + t.  Rotating the whole
    # configuration by R(q_start)^T leaves every distance, and therefore every
    # Tanimoto, unchanged and puts both engines in one frame:
    #     M_eff = R(q_start)^T M      t_eff = R(q_start)^T t
    pose: dict[str, list] = {}
    fold_residual = 0.0
    recon_residual = {}
    for arm in arms:
        rows = np.asarray(f[f"pose/{arm}"], np.float64)
        engine = meta["arms"][arm]["engine"]
        out = []
        worst = 0.0
        for k in range(n):
            M = kernel_rotation_matrix(rows[k, 9:13])
            t = rows[k, 13:16]
            if engine == "roshambo3":
                m_eff, t_eff = M, t
            else:
                rs = R.quaternion_matrix(rows[k, 16:20])
                m_eff, t_eff = rs.T @ M, rs.T @ t
                # the fold must not move the score
                sc = _scorer(int(pq[k]), int(pl[k]), R)
                s_folded = sc(m_eff, t_eff)["tanimoto_shape"]
                aa = _F["q"][int(pq[k])] @ rs.T
                bb = _F["l"][int(pl[k])] @ M.T + t
                s_direct = R.tanimoto(R.pair_overlap(aa, bb),
                                      R.self_overlap(aa),
                                      R.self_overlap(_F["l"][int(pl[k])]))
                fold_residual = max(fold_residual, abs(s_folded - s_direct))
            out.append((m_eff, np.asarray(t_eff, float)))
            # and the folded pose must reproduce this arm's recorded oracle score
            key = f"oracle/{arm}/as_built/tanimoto_shape"
            if key in f.files:
                sc = _scorer(int(pq[k]), int(pl[k]), R)
                worst = max(worst, abs(sc(*out[-1])["tanimoto_shape"]
                                       - float(f[key][k])))
        pose[arm] = out
        recon_residual[arm] = float(worst)
        # ROSHAMBO2 arms are rescored on the very coordinates their recorded
        # oracle score used, so their residual is float64 rounding.  A ROSHAMBO3
        # arm's recorded score was taken on the corpus's int16-quantized
        # coordinates and is re-taken here on ROSHAMBO2's unquantized ones, so
        # its residual is the quantization effect the second experiment bounded
        # at 1.1e-04 -- not a reconstruction error.  Both are gated, at their
        # own scales, rather than eyeballed.
        limit = 1e-12 if engine == "roshambo2" else 2e-4
        if worst > limit:
            raise SystemExit(
                f"arm {arm}: the folded pose reproduces its recorded oracle "
                f"shape Tanimoto only to {worst:.2e}, past the {limit:.0e} this "
                f"frame change can account for; the reconstruction is wrong")
        log(f"[basins] {arm:20s} folded pose reproduces its recorded oracle "
            f"shape Tanimoto to {worst:.2e}")

    # A basin is defined by local ascent from a *rigid* pose.  The pre-fix arm's
    # matrix is not a rotation on three quarters of pairs (T169 second
    # experiment, section 2), so seeding a rigid refinement from it would be
    # refining from a configuration the engine never scored.  It is carried in
    # the fixture and excluded from the mechanism analysis, deliberately.
    rigid_arms, orthogonality = [], {}
    for arm in arms:
        worst = max(float(np.abs(m.T @ m - np.eye(3)).max())
                    for m, _ in pose[arm])
        orthogonality[arm] = worst
        if worst <= 1e-4:
            rigid_arms.append(arm)
    log(f"[basins] rigid arms {rigid_arms}; refinement skipped for "
        f"{[x for x in arms if x not in rigid_arms]}")

    # --- the float64 reference and the local refinements -------------------
    t0 = time.time()
    with ProcessPoolExecutor(a.workers, initializer=_init,
                             initargs=(a.fixture,)) as ex:
        jobs = [(int(pq[k]), int(pl[k]), a.restarts, "combination")
                for k in range(n)]
        g_combo = list(ex.map(_global, jobs, chunksize=1))
        log(f"[basins] combination reference: {time.time() - t0:.0f}s")
        jobs = [(int(pq[k]), int(pl[k]), a.restarts, "shape") for k in range(n)]
        g_shape = list(ex.map(_global, jobs, chunksize=1))
        log(f"[basins] shape reference: {time.time() - t0:.0f}s")
        conv_idx = list(range(0, n, max(1, n // a.convergence_pairs)))[:a.convergence_pairs]
        g_hi = list(ex.map(_global, [(int(pq[k]), int(pl[k]), 2 * a.restarts,
                                      "combination") for k in conv_idx],
                           chunksize=1))
        refined = {}
        for arm in rigid_arms:
            refined[arm] = list(ex.map(
                _refine, [(int(pq[k]), int(pl[k]), _quat_of(pose[arm][k][0]),
                           pose[arm][k][1]) for k in range(n)], chunksize=1))
            log(f"[basins] refined {arm}")
    per_pair_move = {int(f["panel_pair_index"][k]): float(g_hi[i][0]
                                                          - g_combo[k][0])
                     for i, k in enumerate(conv_idx)}
    moved = max(abs(v) for v in per_pair_move.values())
    log(f"[basins] reference convergence at {2 * a.restarts} restarts: "
        f"max move {moved:.2e} over {len(conv_idx)} pairs")
    # Pitfall 4: an unconverged reference is worse than none.  The second
    # experiment's reference converged at 64 restarts on a sample drawn across
    # the whole panel; this fixture is deliberately enriched in the pairs where
    # the two searches disagree, which are exactly the multi-modal ones, so the
    # restart count that sufficed there does not automatically suffice here.
    if moved > 1e-6:
        raise SystemExit(
            f"the reference moved by {moved:.2e} when the restarts were "
            f"doubled: it is not converged at {a.restarts} restarts on this "
            f"fixture and every shortfall below it would be a lower bound. "
            f"Raise --restarts. Per-pair moves: {per_pair_move}")

    ref_combo = np.array([g[0] for g in g_combo])
    ref_shape = np.array([g[0] for g in g_shape])
    ref_pose = [(R.quaternion_matrix(g[1]), g[2]) for g in g_combo]

    # --- per-pair table ----------------------------------------------------
    A, B = a.reference_arm, a.baseline_arm
    rows_out = []
    for k in range(n):
        b_atoms = _F["l"][int(pl[k])]
        q_atoms = _F["q"][int(pq[k])]
        rec = {
            "pair": int(f["panel_pair_index"][k]),
            "query_key": str(f["pair_query_key"][k]),
            "library_key": str(f["pair_library_key"][k]),
            "stratum": str(f["pair_stratum"][k]),
            "selected_for": str(f["selected_for"][k]),
            "is_extreme": bool(f["is_extreme"][k]),
            "bin": {o: str(f[f"isostep_bin/{o}"][k]) for o in OBJECTIVES},
            "isostep_delta": {o: float(f[f"isostep_delta/{o}"][k])
                              for o in OBJECTIVES},
            "reference_combination": float(ref_combo[k]),
            "reference_shape": float(ref_shape[k]),
            "query_atoms": int(len(q_atoms)),
            "library_atoms": int(len(b_atoms)),
            "arms": {},
        }
        rg_q, an_q = gyration(q_atoms)
        rg_l, an_l = gyration(b_atoms)
        rec["query_radius_of_gyration_a"] = rg_q
        rec["library_radius_of_gyration_a"] = rg_l
        rec["query_anisotropy"] = an_q
        rec["library_anisotropy"] = an_l
        for arm in rigid_arms:
            m_e, t_e = pose[arm][k]
            s = _scorer(int(pq[k]), int(pl[k]), R)(m_e, t_e)
            rf, rq, rt = refined[arm][k]
            rm = R.quaternion_matrix(rq)
            sr = _scorer(int(pq[k]), int(pl[k]), R)(rm, rt)
            rec["arms"][arm] = {
                "score": {c: float(s[c]) for c in CH},
                "refined": {c: float(sr[c]) for c in CH},
                "depth_gap": float(rf - s["tanimoto_combination"]),
                "breadth_gap": float(ref_combo[k] - rf),
                "shortfall": float(ref_combo[k] - s["tanimoto_combination"]),
                "angle_to_reference_deg": geodesic_angle_deg(m_e, ref_pose[k][0]),
                "rmsd_to_reference_a": placement_rmsd(b_atoms, m_e, t_e,
                                                      *ref_pose[k]),
                "refined_rmsd_to_reference_a": placement_rmsd(
                    b_atoms, rm, rt, *ref_pose[k]),
                "travel_from_pose_to_refined_a": placement_rmsd(
                    b_atoms, m_e, t_e, rm, rt),
                "reached_reference_basin": bool(
                    ref_combo[k] - rf <= EQUIVALENT_SCORE),
            }
        # the pairwise mechanism, for the two arms the fixture is binned on
        ma, ta = pose[A][k]
        mb, tb = pose[B][k]
        ra_m = R.quaternion_matrix(refined[A][k][1])
        rb_m = R.quaternion_matrix(refined[B][k][1])
        rmsd_final = placement_rmsd(b_atoms, ma, ta, mb, tb)
        rmsd_refined = placement_rmsd(b_atoms, ra_m, refined[A][k][2],
                                      rb_m, refined[B][k][2])
        d_ref = refined[A][k][0] - refined[B][k][0]
        same = rmsd_refined <= SAME_BASIN_RMSD_A
        equiv = abs(d_ref) <= EQUIVALENT_SCORE
        if same:
            cls = "same_basin_depth"
        elif equiv:
            cls = "distinct_equivalent_optima"
        else:
            cls = "different_basin"
        rec["mechanism"] = {
            "final_pose_angle_deg": geodesic_angle_deg(ma, mb),
            "final_pose_rmsd_a": rmsd_final,
            "refined_pose_rmsd_a": rmsd_refined,
            "refined_score_difference": float(d_ref),
            "class": cls,
            "depth_component": float(rec["arms"][B]["depth_gap"]
                                     - rec["arms"][A]["depth_gap"]),
            "breadth_component": float(rec["arms"][B]["breadth_gap"]
                                       - rec["arms"][A]["breadth_gap"]),
            "combination_delta_check": float(
                rec["arms"][A]["score"]["tanimoto_combination"]
                - rec["arms"][B]["score"]["tanimoto_combination"]),
        }
        rec["mechanism"]["identity_residual"] = float(abs(
            rec["mechanism"]["depth_component"]
            + rec["mechanism"]["breadth_component"]
            - rec["mechanism"]["combination_delta_check"]))
        rows_out.append(rec)

    # --- which start won, for the arms that record one ---------------------
    starts = {}
    for arm in arms:
        sq = meta["arms"][arm].get("start_quaternions", [])
        rows = np.asarray(f[f"pose/{arm}"], np.float64)[:, 16:20]
        if len(sq) <= 1:
            starts[arm] = {"recorded": False,
                           "why": "the arm reports a single START_QUAT "
                                  "(identity on the ROSHAMBO3 field path), so "
                                  "which of its internal starts won is not "
                                  "recoverable from the returned row"}
            continue
        sqa = np.asarray(sq, float)
        idx = [int(np.argmin(np.abs(np.abs(sqa @ rows[k]) - 1.0)))
               for k in range(n)]
        starts[arm] = {"recorded": True, "n_starts": len(sq),
                       "winner_index": idx,
                       "histogram": {str(i): int((np.array(idx) == i).sum())
                                     for i in range(len(sq))}}

    # --- aggregates over the fixture (a stratified sample, not the panel) --
    def summarize(sel: np.ndarray) -> dict:
        if not sel.any():
            return {"n": 0}
        cls = [rows_out[k]["mechanism"]["class"] for k in np.flatnonzero(sel)]
        dep = np.array([rows_out[k]["mechanism"]["depth_component"]
                        for k in np.flatnonzero(sel)])
        bre = np.array([rows_out[k]["mechanism"]["breadth_component"]
                        for k in np.flatnonzero(sel)])
        return {
            "n": int(sel.sum()),
            "class_counts": {c: cls.count(c) for c in
                             ("same_basin_depth", "different_basin",
                              "distinct_equivalent_optima")},
            "mean_depth_component": float(dep.mean()),
            "mean_breadth_component": float(bre.mean()),
            "depth_share_of_mean_combo_delta": (
                float(dep.mean() / (dep.mean() + bre.mean()))
                if abs(dep.mean() + bre.mean()) > 1e-12 else None),
        }

    by_cell = {}
    for o in OBJECTIVES:
        bins = np.asarray([str(s) for s in f[f"isostep_bin/{o}"]])
        for b in ("r3_better", "tie", "r2_better", "middle"):
            by_cell[f"{o}:{b}"] = summarize(bins == b)

    # correlations: is the tail just big molecules?
    d_shape = np.array([r["isostep_delta"]["shape"] for r in rows_out])
    d_combo = np.array([r["isostep_delta"]["combination"] for r in rows_out])
    size = np.array([r["library_atoms"] + r["query_atoms"] for r in rows_out])
    rg = np.array([r["library_radius_of_gyration_a"] for r in rows_out])
    aniso = np.array([r["library_anisotropy"] for r in rows_out])
    ref_lvl = ref_combo
    corr = {
        "note": ("Spearman over the fixture's 48 pairs, which is an "
                 "outcome-stratified sample: a correlation here is suggestive "
                 "and is not the panel's correlation"),
        "delta_shape_vs_total_heavy_atoms": spearman(size, d_shape),
        "delta_combination_vs_total_heavy_atoms": spearman(size, d_combo),
        "delta_shape_vs_library_radius_of_gyration": spearman(rg, d_shape),
        "delta_shape_vs_library_anisotropy": spearman(aniso, d_shape),
        "delta_shape_vs_reference_combination": spearman(ref_lvl, d_shape),
        "r3_shortfall_vs_total_heavy_atoms": spearman(
            size, np.array([r["arms"][A]["shortfall"] for r in rows_out])),
        "r2_shortfall_vs_total_heavy_atoms": spearman(
            size, np.array([r["arms"][B]["shortfall"] for r in rows_out])),
    }

    # the shape tail against the objective both engines actually optimize
    shape_bins = np.asarray([str(s) for s in f["isostep_bin/shape"]])
    tail = np.flatnonzero(shape_bins == "r2_better")
    shape_tail = {
        "n": int(len(tail)),
        "combination_delta_positive": int(sum(
            rows_out[k]["isostep_delta"]["combination"] > 0 for k in tail)),
        "mean_combination_delta": float(np.mean(
            [rows_out[k]["isostep_delta"]["combination"] for k in tail]))
        if len(tail) else None,
        "mean_color_delta": float(np.mean(
            [rows_out[k]["isostep_delta"]["color"] for k in tail]))
        if len(tail) else None,
        "what_this_asks": ("both engines optimize the MIXED objective, so a "
                           "shape loss at a better combination score is a "
                           "trade along the objective, not a worse optimum"),
    }

    rec = {
        "fixture": str(a.fixture),
        "n_pairs": n,
        "restarts": a.restarts,
        "reference_arm": A,
        "baseline_arm": B,
        "same_basin_rmsd_threshold_a": SAME_BASIN_RMSD_A,
        "equivalent_score_threshold": EQUIVALENT_SCORE,
        "color_accelerator_max_relative_error": fast_err,
        "controls": {
            "pose_fold_max_score_change": float(fold_residual),
            "folded_pose_reproduces_recorded_oracle_score": recon_residual,
            "reference_convergence": {
                "restarts_low": a.restarts, "restarts_high": 2 * a.restarts,
                "n_pairs": len(conv_idx), "max_abs_move": float(moved),
                "per_pair_move": per_pair_move,
                "verdict": "converged" if moved <= 1e-6 else "NOT converged",
            },
            "max_decomposition_identity_residual": float(max(
                r["mechanism"]["identity_residual"] for r in rows_out)),
            "n_arms_above_reference": {
                arm: int(sum(r["arms"][arm]["shortfall"] < -1e-6
                             for r in rows_out)) for arm in rigid_arms},
            "arm_max_orthogonality_error": orthogonality,
            "arms_excluded_from_the_mechanism_analysis": [
                x for x in arms if x not in rigid_arms],
        },
        "overall": summarize(np.ones(n, bool)),
        "by_cell": by_cell,
        "shape_tail_against_the_mixed_objective": shape_tail,
        "correlations": corr,
        "starts": starts,
        "pairs": rows_out,
    }
    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rec, indent=2) + "\n")
    log(f"[basins] wrote {outp}")
    log(f"[basins] overall {rec['overall']['class_counts']}")
    return 0


def _quat_of(m: np.ndarray) -> np.ndarray:
    """Unit quaternion of a rotation matrix, for seeding a refinement."""
    tr = float(np.trace(m))
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = np.array([0.25 * s, (m[2, 1] - m[1, 2]) / s,
                      (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s])
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = np.array([(m[2, 1] - m[1, 2]) / s, 0.25 * s,
                      (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s])
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = np.array([(m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s,
                      0.25 * s, (m[1, 2] + m[2, 1]) / s])
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = np.array([(m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s,
                      (m[1, 2] + m[2, 1]) / s, 0.25 * s])
    return q / np.linalg.norm(q)


if __name__ == "__main__":
    raise SystemExit(main())
