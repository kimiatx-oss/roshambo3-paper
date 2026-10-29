"""Tests for the cross-backend portability table."""

from __future__ import annotations

import copy
import re
import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_portability", ROOT / "scripts" / "analyze_portability.py")
portability = importlib.util.module_from_spec(SPEC)
sys.modules["analyze_portability"] = portability
SPEC.loader.exec_module(portability)

MODES = ["shape", "rescore", "combo"]
QUERIES = ["q0", "q1"]
K = 4
PANEL = "e" * 64
FROZEN, PATCHED = "a" * 40, "c" * 40


def device_spec():
    return {
        "modes": MODES, "top_k": K,
        "min_timed_repeats": {"cuda": 2, "cpu": 2, "metal": 2},
        "commits": {FROZEN: "frozen", PATCHED: "frozen plus an AArch64-only fix"},
        "default_commit": FROZEN,
        "devices": [
            {"key": "ref", "name": "Reference GPU", "kind": "gpu", "backend": "cuda", "reference": True},
            {"key": "arm", "name": "Some CPU", "kind": "cpu", "backend": "cpu"},
            {"key": "mac", "name": "Some Apple GPU", "kind": "gpu", "backend": "metal"},
        ],
    }


def report(backend: str, mode: str, walls=(2.0, 1.0, 3.0)) -> dict:
    compute = ({"gpu": {"lock_held": True}} if backend == "cuda" else
               {"host_compute": {"lock_held": True,
                                 "cpu": {"physical_cores": 16, "logical_cpus": 16},
                                 "metal": {"hardware": [{"sppci_cores": 20}]}}})
    return {
        "corpus": {"conformers": 1000, "name": "LIT-PCBA", "ids_sha256": "1" * 64,
                   "descriptor_sha256": "3" * 64, "fingerprint": "2" * 64},
        "query_preparation": {"queries": [{"name": q} for q in QUERIES]},
        "git": {"sha": "a" * 40, "dirty": False},
        # Only the CUDA extension stamps a commit.
        "tool": {"git_sha": FROZEN if backend == "cuda" else "unknown"},
        "screen": {"mode": mode, "backend": backend, "top_k": K, "level": "molecule",
                   "cache_mode": "warm",
                   "repeats": [{"screen_call_wall_s": w} for w in walls]},
        "screen_size": {"conformer_pairs_per_repeat": 2_000_000},
        **compute,
    }


def env_record(backend: str, **install) -> dict:
    return {"install": {"checkout_head": FROZEN, "checkout_status": "", "editable": False,
                        **install},
            "panel_sha256": PANEL,
            "tool_stamps": {"cpu": {"selected_target": "AVX512F" if backend == "cpu" else "X86_64_V3"}}}


def write_device(runs: Path, key: str, backend: str, hits: dict, edit=None, env_edit=None):
    directory = runs / key
    directory.mkdir(parents=True)
    env = env_record(backend)
    if env_edit:
        env_edit(env)
    (directory / "env.json").write_text(json.dumps(env))
    for mode in MODES:
        record = report(backend, mode)
        if edit:
            edit(record)
        (directory / f"panel8-{mode}.json").write_text(json.dumps(record))
        with (directory / f"panel8-{mode}.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["query", "rank", "mol_id"])
            for query, mols in hits.items():
                for rank, mol in enumerate(mols, start=1):
                    writer.writerow([query, rank, mol])


REFERENCE = {"q0": ["1", "2", "3", "4"], "q1": ["5", "6", "7", "8"]}


class PortabilityTests(unittest.TestCase):
    def build(self, runs: Path, arm_edit=None, arm_hits=None, env_edit=None):
        write_device(runs, "ref", "cuda", REFERENCE)
        write_device(runs, "arm", "cpu", arm_hits or {"q0": ["1", "2", "3", "9"],
                                                      "q1": ["8", "7", "6", "5"]},
                     edit=arm_edit, env_edit=env_edit)

    def test_rates_and_molecule_recall(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs)
            result = portability.analyze(runs, device_spec(), PANEL)
        self.assertEqual(result["missing"], ["mac"])
        ref, arm = result["rows"]
        self.assertAlmostEqual(ref["rates"]["combo"], 1_000_000.0)   # 2e6 pairs / median 2 s
        self.assertIsNone(ref["recall_mean"])
        self.assertAlmostEqual(arm["recall_mean"], (0.75 + 1.0) / 2)  # order inside top-K is irrelevant
        self.assertAlmostEqual(arm["recall_min"], 0.75)
        self.assertEqual(arm["detail"], "16C/16T, AVX-512")
        tex = portability.table_tex(result)
        self.assertIn(r"\label{tab:portability}", tex)
        self.assertIn("Some CPU, 16C/16T, AVX-512 & 1.000 & 1.000 & 1.000 & --- & 87.5 (75.0)", tex)
        self.assertIn(r"Reference GPU (CUDA) & 1.00 & 1.00 & 1.00 & --- & reference", tex)
        self.assertIn(r"\multicolumn{3}{c}{M pairs/s}", tex)
        pending = portability.table_tex(result, device_spec())
        self.assertIn(r"Some Apple GPU (Metal) & \multicolumn{5}{c}{\emph{pending}}", pending)

    def test_cloud_cpus_report_combo_per_vcpu(self):
        spec = device_spec()
        spec["devices"][1]["cloud"] = True
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs)
            result = portability.analyze(runs, spec, PANEL)
        tex = portability.table_tex(result, spec)
        # 1e6 combo pairs/s over 16 logical CPUs: 125 K pairs/s per two vCPUs.
        self.assertIn(r"Some CPU, 16C/16T, AVX-512 & 1.000 & 1.000 & 1.000 & 125.0 &", tex)
        # The main-text table names no commit and marks no cloud VM; the appendix does.
        self.assertNotIn("dagger", tex)
        self.assertNotIn("texttt", tex)

    def test_a_device_may_run_a_declared_second_commit(self):
        spec = device_spec()
        spec["devices"][1]["commit"] = PATCHED
        patched = lambda r: r["git"].update(sha=PATCHED)
        moved = lambda e: e["install"].update(checkout_head=PATCHED)
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs, arm_edit=patched, env_edit=moved)
            result = portability.analyze(runs, spec, PANEL)
            with self.assertRaises(ValueError):          # the reference must stay on FROZEN
                portability.analyze(runs, device_spec(), PANEL)
        self.assertEqual(list(result["commits"]), [FROZEN, PATCHED])
        undeclared = copy.deepcopy(spec)
        undeclared["devices"][1]["commit"] = "f" * 40
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs)
            with self.assertRaises(ValueError):
                portability.analyze(runs, undeclared, PANEL)

    def test_incomparable_rows_are_refused(self):
        edits = {
            "commit": lambda r: r["git"].update(sha="c" * 40),
            "dirty": lambda r: r["git"].update(dirty=True),
            "tool": lambda r: r["tool"].update(git_sha="d" * 40),
            "lock": lambda r: r["host_compute"].update(lock_held=False),
            "corpus": lambda r: r["corpus"].update(conformers=999),
            "corpus content": lambda r: r["corpus"].update(descriptor_sha256="f" * 64),
            "corpus build": lambda r: r["corpus"].update(fingerprint="f" * 64),
            "repeats": lambda r: r["screen"].update(repeats=[{"screen_call_wall_s": 1.0}]),
            "cold": lambda r: r["screen"].update(cache_mode="cold"),
            "level": lambda r: r["screen"].update(level="conformer"),
        }
        for name, edit in edits.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                runs = Path(temp)
                self.build(runs, arm_edit=edit)
                with self.assertRaises(ValueError):
                    portability.analyze(runs, device_spec(), PANEL)

    def test_unstamped_tool_takes_its_commit_from_a_clean_install_only(self):
        envs = {
            "other checkout": lambda e: e["install"].update(checkout_head=PATCHED),
            "dirty checkout": lambda e: e["install"].update(checkout_status=" M src/x.py\n"),
            "editable": lambda e: e["install"].update(editable=True),
            "panel": lambda e: e.update(panel_sha256="f" * 64),
        }
        for name, edit in envs.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as temp:
                runs = Path(temp)
                self.build(runs, env_edit=edit)
                with self.assertRaises(ValueError):
                    portability.analyze(runs, device_spec(), PANEL)

    def test_missing_env_record_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs)
            (runs / "arm" / "env.json").unlink()
            with self.assertRaises(ValueError):
                portability.analyze(runs, device_spec(), PANEL)

    def test_constants_are_pending_until_every_device_reports(self):
        spec = device_spec()
        for device, stem in zip(spec["devices"], ("Ref", "Arm", "Mac")):
            device["macro"] = stem
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs)
            result = portability.analyze(runs, spec, PANEL)
        tex = portability.constants_tex(result, spec)
        self.assertIn(r"\newcommand{\PortabilityWorstRecallPercent}{\textbf{??}}", tex)
        # Only the Metal GPU is missing, so the CPU-only ratio is already final.
        self.assertIn(r"\newcommand{\PortabilityReferenceOverFastestCpuCombo}{1}", tex)
        result["missing"] = []
        tex = portability.constants_tex(result, spec)
        self.assertIn(r"\newcommand{\PortabilityWorstRecallPercent}{75.0}", tex)
        self.assertIn(r"\newcommand{\PortabilityLowestMeanRecallPercent}{87.5}", tex)
        self.assertIn(r"\newcommand{\PortabilityReferenceOverFastestCpuCombo}{1}", tex)
        low = re.search(r"\\PortabilityReferenceOverFastestCpuLow\}\{(\d+)\}", tex)
        high = re.search(r"\\PortabilityReferenceOverFastestCpuHigh\}\{(\d+)\}", tex)
        self.assertLessEqual(int(low.group(1)), int(high.group(1)))

    def test_exactly_one_reference_with_runs(self):
        spec = device_spec()
        no_reference = copy.deepcopy(spec)
        no_reference["devices"][0]["reference"] = False
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            self.build(runs)
            with self.assertRaises(ValueError):
                portability.analyze(runs, no_reference, PANEL)
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp)
            write_device(runs, "arm", "cpu", REFERENCE)
            with self.assertRaises(ValueError):
                portability.analyze(runs, spec, PANEL)

    def test_only_the_runs_own_outputs_may_dirty_the_tree(self):
        outputs = {"dirty": True, "source_dirty_paths": ["publication/runs/portability/"]}
        self.assertFalse(portability.source_was_dirty(outputs))
        edited = {"dirty": True, "source_dirty_paths": ["publication/runs/portability/",
                                                        "src/roshambo3/api.py"]}
        self.assertTrue(portability.source_was_dirty(edited))
        self.assertTrue(portability.source_was_dirty({"dirty": True}))
        truncated = {"dirty": True, "source_dirty_paths": ["publication/runs/portability/"] * 20}
        self.assertTrue(portability.source_was_dirty(truncated))

    def test_metal_detail_reads_gpu_cores_from_the_record(self):
        device = {"backend": "metal"}
        self.assertEqual(portability.device_detail(device, report("metal", "shape")), "20 cores")

    def test_short_reference_list_is_an_error(self):
        with self.assertRaises(ValueError):
            portability.recall_at_k(["1"], ["1"], 4)


if __name__ == "__main__":
    unittest.main()
