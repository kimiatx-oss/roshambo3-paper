"""Tests for paper asset generation and release boundaries."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assets = load_module("generate_paper_assets", ROOT / "scripts/generate_paper_assets.py")


class AssetTests(unittest.TestCase):
    def test_read_timing_uses_measured_median_and_pair_rate(self):
        report = {
            "corpus": {"conformers": 10},
            "query_preparation": {"n_queries": 2},
            "screen": {
                "mode": "shape",
                "timed_repeats_requested": 3,
                "repeats": [
                    {"phase": "timed", "screen_call_wall_s": 4, "kernel_s": 3},
                    {"phase": "timed", "screen_call_wall_s": 2, "kernel_s": 1},
                    {"phase": "timed", "screen_call_wall_s": 3, "kernel_s": 2},
                ],
            },
            "screen_size": {"conformer_pairs_per_repeat": 20},
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            timing = assets.read_timing("GPU", "shape", path)
        self.assertEqual(timing.median_wall_s, 3)
        self.assertEqual(timing.median_kernel_s, 2)
        self.assertAlmostEqual(timing.evaluations_per_s, 20 / 3)

    def test_incomplete_repeat_set_is_rejected(self):
        report = {
            "screen": {"mode": "shape", "timed_repeats_requested": 2, "repeats": []}
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                assets.read_timing("GPU", "shape", path)

    def test_saturation_svg_contains_every_measured_arm(self):
        def timing(queries, rate):
            return assets.Timing(
                machine="GPU",
                mode="combo",
                source=Path("report.json"),
                queries=queries,
                conformers=10,
                repeats=3,
                median_wall_s=1,
                median_kernel_s=1,
                evaluations_per_s=rate * 1e6,
            )

        results = {
            "saturation": {
                queries: timing(queries, rate)
                for queries, rate in ((1, 10.5), (2, 13), (4, 16), (8, 17), (16, 18))
            }
        }
        svg = assets.saturation_svg(results)
        self.assertEqual(svg.count('<circle cx="'), 5)
        for query_count in (1, 2, 4, 8, 16):
            self.assertIn(f">{query_count}</text>", svg)
        self.assertIn("log2 spacing", svg)
        self.assertNotIn("saturation plateau", svg)

    def test_field_schematic_names_value_gradient_and_pair_matrix(self):
        svg = assets.field_schematic_svg()
        self.assertIn("value + gradient", svg)
        self.assertIn("every matrix cell", svg)
        self.assertIn("A × B Gaussians per step", svg)

    def test_paper_measurements_are_derived_from_archived_records(self):
        results = assets.current_results(ROOT / "runs")
        self.assertAlmostEqual(
            results["combo_device_share_of_gap_percent"], 99.5, places=1
        )
        self.assertAlmostEqual(results["step_budget_ratio"], 3.272512514686871)
        self.assertEqual(results["dudez_shape"]["n_targets"], 43)
        # LIT-PCBA conformer counts, recomputed from the format-3 corpus's run tables.
        counts = results["litpcba_counts"]
        self.assertEqual(counts["source_compounds"], 407983)
        self.assertEqual(counts["compounds_without_conformers"], 319)
        self.assertEqual(counts["histogram"][50], 407499)
        self.assertEqual(round(counts["source_sdf"]["bytes"] / 1e9, 1), 78.9)
        # Field* cells: the shipped update rule on the declared subset, not rows[0].
        self.assertEqual(results["field"]["update_rule"], "ADAGRAD_EXP")
        self.assertEqual(results["field"]["n_conf"], 300000)
        self.assertAlmostEqual(results["field"]["recall_at_1000_panel"], 0.99525)
        # Volta speedups: T114's ROSHAMBO2 walls over the public TITAN V walls.
        for key, expected in (("shape_corrected", 78.5), ("shape_stock", 177.1),
                              ("combo_stock", 154.3), ("combo_corrected", 175.2)):
            self.assertAlmostEqual(results[key]["ratio_search_only"], expected, places=1)
        self.assertAlmostEqual(results["shape_stock"]["roshambo3_wall_s"], 7.829, places=3)
        self.assertAlmostEqual(results["dudez_shape"]["estimate"], -0.0366227921)
        self.assertAlmostEqual(results["dudez_combo"]["estimate"], 0.0122701472)
        counts = results["development_counts"]
        tickets = assets.development_tickets(ROOT / "runs")
        self.assertEqual(counts["tickets"], len(tickets))
        self.assertLessEqual(counts["closed_tickets"], counts["tickets"])
        self.assertLessEqual(counts["longest_chain"], counts["tickets"])
        self.assertGreaterEqual(counts["decisions"], 32)
        self.assertGreaterEqual(counts["pitfalls"], 32)

    def test_systems_table_lists_every_machine_and_checks_records(self):
        context = json.loads((ROOT / "data/experimental-context.json").read_text())
        table = assets.systems_table(ROOT / "runs", context)
        self.assertEqual(table.count(r" \\"), len(context["systems_order"]) + 2)
        self.assertIn("GCP c4a-highcpu-16", table)
        context["systems"]["c4"]["threads"] = 32
        with self.assertRaisesRegex(ValueError, "threads"):
            assets.systems_table(ROOT / "runs", context)

    def test_main_table_orders_both_baselines_alike_and_includes_parity(self):
        table = assets.main_results_table({})
        self.assertIn("DUDE-Z shape parity", table)
        self.assertIn("DUDE-Z combo parity", table)
        self.assertIn("vs. color-skip / as-released ROSHAMBO2", table)
        self.assertIn(r"\VoltaComboCorrectedSpeedup$\times$ / \VoltaComboStockSpeedup", table)
        self.assertLess(
            table.index("VoltaShapeCorrectedSpeedup"),
            table.index("VoltaShapeStockSpeedup"),
        )

    def test_longest_dependency_chain_counts_tickets_not_edges(self):
        def ticket(ident, depends=""):
            return {"id": ident, "depends_on": depends}
        tickets = [ticket("T1"), ticket("T2", "T1"), ticket("T3", "T1 T2"), ticket("T4")]
        self.assertEqual(assets.longest_dependency_chain(tickets), 3)
        with self.assertRaises(ValueError):
            assets.longest_dependency_chain([ticket("T1", "T2"), ticket("T2", "T1")])

    def test_ticket_timeline_marks_each_milestone_and_reaches_the_last(self):
        milestones = json.loads((ROOT / assets.TICKET_MILESTONES).read_text())["milestones"]
        drawn = assets.ticket_timeline_svg(ROOT / "runs", ROOT / assets.TICKET_MILESTONES)
        self.assertTrue(drawn.startswith("<svg"))
        for milestone in milestones:
            self.assertIn(f">{milestone['label']}</text>", drawn)
        self.assertNotIn("<circle", drawn)
        self.assertIn(">Oct 31</text>", drawn)

    def test_ticket_strip_circles_each_epochs_largest_burst(self):
        tickets = assets.development_tickets(ROOT / "runs")
        bursts = {b["epoch"]: b["members"] for b in assets.ticket_bursts(tickets)}
        self.assertEqual(sorted(bursts), sorted(["plan", "gpu", "cpu-port", "cpu-color", "cpu-combo",
                                                  "native", "metal", "format3"]))
        self.assertEqual([t["id"] for t in bursts["plan"]][:2], ["T01", "T02"])
        self.assertTrue(all(len(m) >= assets.BURST_MIN_TICKETS for m in bursts.values()))
        drawn = assets.ticket_strip_svg(ROOT / "runs")
        self.assertEqual(drawn.count("<ellipse"), len(bursts))
        # A declared span replaces the epoch's burst with that ticket range.
        spans = json.loads((ROOT / assets.TICKET_CALLOUTS).read_text())["spans"]
        spanned = {b["epoch"]: b["members"] for b in assets.ticket_bursts(tickets, spans)}
        self.assertEqual([spanned["cpu-combo"][i]["id"] for i in (0, -1)],
                         [spans["cpu-combo"]["first"], spans["cpu-combo"]["last"]])
        self.assertEqual(sorted(spanned), sorted(bursts))
        labels = {e["key"]: e["label"] for e in json.loads(
            (ROOT / "runs" / assets.DEVELOPMENT_RECORD / "record.json").read_text())["epochs"]}
        for epoch in bursts:
            self.assertIn(f">{labels[epoch]}</text>", drawn)
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "callouts.json"
            bad.write_text(json.dumps({"sides": {"plan": "sideways"}}))
            with self.assertRaisesRegex(ValueError, "unknown callout side"):
                assets.ticket_strip_svg(ROOT / "runs", ROOT / assets.TICKET_MILESTONES, bad)

    def test_pitfall_classes_cover_every_pitfall_once(self):
        table = assets.pitfall_classes_table(ROOT / "runs", ROOT / assets.PITFALL_CLASSES)
        self.assertIn(r"\label{tab:pitfall-classes}", table)
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / "classes.json"
            classes = json.loads((ROOT / assets.PITFALL_CLASSES).read_text())
            classes["classes"][0]["pitfalls"].append(classes["classes"][1]["pitfalls"][0])
            broken.write_text(json.dumps(classes))
            with self.assertRaises(ValueError):
                assets.pitfall_classes_table(ROOT / "runs", broken)

    def test_incident_constants_require_a_number_and_a_source(self):
        tex = assets.development_constants_tex(ROOT / assets.DEVELOPMENT_INCIDENTS)
        self.assertIn(r"\newcommand{\StopRulePlannedOverrunFactor}{129}", tex)
        self.assertIn(r"\newcommand{\StopRuleExecutedOverrunFactor}{64}", tex)
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / "incidents.json"
            broken.write_text(json.dumps({"incidents": [
                {"command": "Bad", "value": "about 5", "source": "x"}]}))
            with self.assertRaises(ValueError):
                assets.development_constants_tex(broken)


if __name__ == "__main__":
    unittest.main()
