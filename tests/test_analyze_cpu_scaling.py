"""Tests for the CPU thread-scaling table."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_cpu_scaling", ROOT / "scripts" / "analyze_cpu_scaling.py")
scaling = importlib.util.module_from_spec(SPEC)
sys.modules["analyze_cpu_scaling"] = scaling
SPEC.loader.exec_module(scaling)

PAIRS = 1_000_000
# arm -> (workers, wall seconds): 1x1 takes 16 s, so rate = PAIRS / wall.
ARMS = {"1x1": (1, 16.0), "4x1": (4, 4.0), "4x2": (8, 3.2), "8x1": (8, 2.0), "all": (16, 1.6)}
HITS = ["3", "1", "2"]


X86 = {"physical_cores": 8, "logical_cpus": 16}
HYBRID = {"physical_cores": 14, "logical_cpus": 14, "performance_cores": 10, "efficiency_cores": 4}


def write_arm(root: Path, arm: str, workers: int, wall: float, edit=None, hits=HITS, affinity=None,
              cpu=X86):
    directory = root / arm
    directory.mkdir(parents=True)
    for mode in scaling.MODES:
        report = {
            "git": {"sha": "a" * 40, "dirty": False},
            "corpus": {"conformers": PAIRS},
            "query_preparation": {"queries": [{"name": "q0"}]},
            "screen": {"backend": "cpu", "mode": mode, "cache_mode": "warm",
                       "workers_resolved": workers,
                       "repeats": [{"screen_call_wall_s": w} for w in (wall, wall * 2, wall)]},
            "screen_size": {"conformer_pairs_per_repeat": PAIRS},
            "host_compute": {"lock_held": True, "cpu": dict(cpu)},
        }
        if edit:
            edit(report)
        prefix = directory / f"panel1-{mode}"
        prefix.with_suffix(".json").write_text(json.dumps(report))
        run = {"affinity": affinity if affinity is not None else
               (list(range(workers)) if arm != "all" else list(range(16)))}
        Path(f"{prefix}.run.json").write_text(json.dumps(run))
        with prefix.with_suffix(".csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["query", "rank", "mol_id"])
            for rank, mol in enumerate(hits, start=1):
                writer.writerow(["q0", rank, mol])


def build(runs: Path, key="x86", edit_arm=None, edit=None, hits=None, affinity=None):
    for arm, (workers, wall) in ARMS.items():
        write_arm(runs / key, arm, workers, wall,
                  edit=edit if arm == edit_arm else None,
                  hits=hits if (hits and arm == edit_arm) else HITS,
                  affinity=affinity if arm == edit_arm else None)


class ScalingTests(unittest.TestCase):
    def test_speedup_efficiency_and_smt_contrasts(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            build(runs)
            result = scaling.analyze(runs, {"x86": "a" * 40, "absent": "a" * 40})
        host, = result["hosts"]
        self.assertEqual([r["arm"] for r in host["rows"]], ["1x1", "4x1", "4x2", "8x1", "all"])
        rows = {r["arm"]: r for r in host["rows"]}
        self.assertAlmostEqual(rows["1x1"]["rates"]["combo"], PAIRS / 16.0)   # median of the repeats
        self.assertAlmostEqual(rows["8x1"]["speedup"]["combo"], 8.0)
        self.assertAlmostEqual(rows["all"]["efficiency"]["combo"], 10.0 / 16)
        self.assertAlmostEqual(host["smt_contrasts"]["4x2/4x1"]["shape"], 1.25)
        self.assertAlmostEqual(host["smt_contrasts"]["all/8x1"]["shape"], 1.25)
        self.assertAlmostEqual(host["smt_contrasts"]["4x2/8x1"]["shape"], 0.625)
        self.assertTrue(all(host["identical_topk"].values()))
        tex = scaling.table_tex(result, {"x86": "Some Xeon"})
        self.assertIn(r"\label{tab:cpu-scaling}", tex)
        self.assertIn(r"Some Xeon & 1$\times$1 & 1 & 62 & 62 & 62 & --- \\", tex)
        self.assertIn(r" & 4$\times$2 & 8 & 312 & 312 & 312 & $+25$\% \\", tex)
        self.assertIn(r" & 8$\times$2 & 16 & 625 & 625 & 625 & $+25$\% \\", tex)
        self.assertNotIn(" all ", tex)
        self.assertEqual(result["missing"], ["absent"])
        self.assertIn(r"absent & \multicolumn{6}{c}{\emph{pending}} \\", tex)

    def test_hosts_may_run_different_declared_commits(self):
        patched = lambda r: r["git"].update(sha="c" * 40)
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            build(runs)
            for arm in ("1x1", "8x1", "all"):
                write_arm(runs / "arm64", arm, *ARMS[arm], edit=patched)
            result = scaling.analyze(runs, {"x86": "a" * 40, "arm64": "c" * 40})
            with self.assertRaises(ValueError):
                scaling.analyze(runs, {"x86": "a" * 40, "arm64": "a" * 40})
        tex = scaling.table_tex(result, {"x86": "Some Xeon", "arm64": "Some ARM"})
        # The caption names no commit; the records carry it.
        self.assertNotIn("aaaaaaaaaa", tex)
        self.assertNotIn("texttt", tex)

    def test_constants(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            build(runs)
            result = scaling.analyze(runs, {"x86": "a" * 40, "absent": "a" * 40})
        tex = scaling.constants_tex(result, {"x86": "Xeon", "absent": "Arm"})
        self.assertIn(r"\newcommand{\ScalingXeonEightCoreEfficiencyPercent}{100}", tex)
        self.assertIn(r"\newcommand{\ScalingXeonSmtGainPercent}{25}", tex)
        self.assertIn(r"\newcommand{\ScalingXeonSmtGainFourCorePercent}{25}", tex)
        self.assertIn(r"\newcommand{\ScalingArmAllEfficiencyPercent}{\textbf{??}}", tex)
        self.assertIn(r"\newcommand{\ScalingIdenticalTopKHostCount}{\textbf{??}}", tex)
        self.assertIn(r"\newcommand{\ScalingHostCount}{2}", tex)
        result["missing"] = []
        self.assertIn(r"\newcommand{\ScalingIdenticalTopKHostCount}{1}",
                      scaling.constants_tex(result, {"x86": "Xeon"}))

    def test_no_smt_host_has_no_contrasts(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            for arm in ("1x1", "8x1", "all"):
                write_arm(runs / "arm64", arm, *ARMS[arm])
            host, = scaling.analyze(runs, {"arm64": "a" * 40})["hosts"]
        self.assertEqual(host["smt_contrasts"], {})

    def test_reordered_hits_are_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            build(runs, edit_arm="4x2", hits=["1", "3", "2"])
            host, = scaling.analyze(runs, {"x86": "a" * 40})["hosts"]
        self.assertFalse(host["identical_topk"]["combo"])

    def test_incomparable_arms_are_refused(self):
        edits = {
            "commit": lambda r: r["git"].update(sha="b" * 40),
            "dirty": lambda r: r["git"].update(dirty=True),
            "lock": lambda r: r["host_compute"].update(lock_held=False),
            "workers": lambda r: r["screen"].update(workers_resolved=16),
            "backend": lambda r: r["screen"].update(backend="cuda"),
        }
        for name, edit in edits.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                runs = Path(temp)
                build(runs, edit_arm="4x2", edit=edit)
                with self.assertRaises(ValueError):
                    scaling.analyze(runs, {"x86": "a" * 40})
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            build(runs, edit_arm="4x2", affinity=[0, 1, 2, 3])
            with self.assertRaises(ValueError):
                scaling.analyze(runs, {"x86": "a" * 40})

    def test_unpinned_thread_counts_measure_against_the_fewest(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            write_arm(runs / "mac", "t4", 4, 4.0, affinity=[], cpu=HYBRID)
            write_arm(runs / "mac", "t14", 14, 1.6, affinity=[], cpu=HYBRID)
            write_arm(runs / "mac", "t10", 10, 2.0, affinity=[], cpu=HYBRID)
            host, = scaling.analyze(runs, {"mac": "a" * 40})["hosts"]
        self.assertEqual([r["arm"] for r in host["rows"]], ["t4", "t10", "t14"])
        self.assertEqual(host["baseline_arm"], "t4")
        rows = {r["arm"]: r for r in host["rows"]}
        self.assertAlmostEqual(rows["t10"]["efficiency"]["combo"], 2.0 * 4 / 10)
        self.assertEqual([r["label"] for r in host["rows"]], ["4+0", "10+0", "10+4"])
        self.assertIsNone(rows["t10"]["extra_gain"])
        self.assertAlmostEqual(rows["t14"]["extra_gain"]["combo"], 0.25)   # 2.0 s -> 1.6 s
        tex = scaling.constants_tex({"hosts": [host], "missing": []}, {"mac": "Mac"})
        self.assertIn(r"\newcommand{\ScalingMacEcoreGainPercent}{25}", tex)
        self.assertIn(r"\newcommand{\ScalingMacShapePerPcoreThousand}{50}", tex)    # 1e6/2 s/10
        self.assertIn(r"\newcommand{\ScalingMacShapePerEcoreThousand}{31}", tex)    # (625-500)/4
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            write_arm(runs / "mac", "t8", 4, 4.0)
            with self.assertRaises(ValueError):
                scaling.analyze(runs, {"mac": "a" * 40})

    def test_no_arms_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            (runs / "x86").mkdir()
            with self.assertRaises(ValueError):
                scaling.analyze(runs, {"x86": "a" * 40})


if __name__ == "__main__":
    unittest.main()
