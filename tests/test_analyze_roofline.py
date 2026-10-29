"""Tests for the deterministic roofline work model."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("analyze_roofline", ROOT / "scripts/analyze_roofline.py")
roofline = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["analyze_roofline"] = roofline
spec.loader.exec_module(roofline)


LADDER = "runs/roofline-ladder-3bb39f69/ladder-summary.json"
TITAN_LADDER = "runs/roofline-ladder-l4-3bb39f69/ladder-summary.json"


class RooflineTests(unittest.TestCase):
    def test_fixed_work_counts_include_final_field_pass(self):
        report = {
            "corpus": {"conformers": 2},
            "query_preparation": {"n_queries": 2, "queries": [{"heavy_atoms": 3}, {"heavy_atoms": 5}]},
            "screen": {"mode": "shape", "timed_repeats_requested": 1,
                       "repeats": [{"phase": "timed", "kernel_s": 2, "screen_call_wall_s": 3}]}}
        inputs = {
            "optimizer": {"steps": 25, "starts": 4, "field_evaluations_per_start": 26},
            "corpus": {"conformers": 2, "real_atoms": 7},
            "source_level_accounting": {
                "convention": "test", "analytic_optimizer_elementary_flops_per_shape_pair_term": 18,
                "field_search_elementary_flops_per_shape_sample": 49,
                "exact_rescore_elementary_flops_per_shape_pair_term": 9,
                "library_transform_elementary_flops_per_atom": 18,
                "half4_node_bytes": 8, "trilinear_nodes_per_sample": 8, "scope_note": "test"}}
        work = roofline.derive(report, inputs)["semantic_work"]
        self.assertEqual(work["field_passes_per_pair"], 104)
        self.assertEqual(work["field_shape_texture_samples"], 104 * 7 * 2)
        self.assertEqual(work["analytic_optimizer_shape_gaussian_terms"], 104 * 7 * 8)
        self.assertEqual(work["field_exact_rescore_shape_gaussian_terms"], 7 * 8)

    def test_d5_snapshot_matches_headline_run(self):
        report = json.loads((ROOT / "runs/public-3bb39f69/blackwell/d5/panel4-shape.json").read_text())
        inputs = json.loads((ROOT / "data/roofline-work-model.json").read_text())
        work = roofline.derive(report, inputs)["semantic_work"]
        self.assertEqual(work["field_shape_texture_samples"], 5297229238912)
        self.assertEqual(work["field_exact_rescore_shape_gaussian_terms"], 1489845723444)

    def test_pubchem_io_accounting_separates_disk_h2d_and_copy_time(self):
        report = json.loads((ROOT / "runs/public-3bb39f69/blackwell/d5/panel4-shape.json").read_text())
        inputs = json.loads((ROOT / "data/roofline-work-model.json").read_text())
        io = roofline.derive(report, inputs)["io_accounting"]
        self.assertEqual(io["cache_mode"], "warm")
        self.assertEqual(io["h2d_bytes"], 92270214168)
        self.assertAlmostEqual(io["stored_bytes_per_wall_s"] / 1e9, 1.70, places=2)
        self.assertAlmostEqual(io["h2d_bytes_per_wall_s"] / 1e9, 2.49, places=2)
        self.assertAlmostEqual(io["h2d_bytes_per_active_copy_s"] / 1e9, 25.30, places=2)
        # Host-decoded int16 coordinates plus per-conformer counts outweigh the
        # bit-packed stored corpus (format 3; T313 removed the pair index).
        self.assertGreater(io["h2d_to_stored_byte_ratio"], 1.4)
        self.assertAlmostEqual(io["coordinate_decode_ratio"], 1.50, places=2)

    def test_device_roof_snapshot_and_power_cap_classification(self):
        headline = json.loads((ROOT / "runs/public-3bb39f69/blackwell/d5/panel4-shape.json").read_text())
        titan = json.loads((ROOT / "runs/public-3bb39f69/titanv/d5/panel4-shape.json").read_text())
        inputs = json.loads((ROOT / "data/roofline-work-model.json").read_text())
        ladder = roofline.load_ladder(ROOT / LADDER)
        with self.assertRaisesRegex(ValueError, "not calibrated"):
            roofline.device_model(roofline.ladder_demands(ladder), inputs, headline, titan)
        cal = roofline.ladder_l1tex_calibration(ladder)
        # Same derivation as the August single-profile value (4.51); every launch agrees within 3%.
        self.assertAlmostEqual(cal["sectors_per_sm_cycle"], 4.49, places=2)
        self.assertGreater(cal["min_sectors_per_sm_cycle"], 4.3)
        self.assertLess(cal["max_sectors_per_sm_cycle"], 4.6)
        inputs["devices"]["blackwell"]["l1tex_sectors_per_sm_cycle"] = cal["sectors_per_sm_cycle"]
        # GV100 takes its demand from the sm_89 ladder (same atom-loop codegen as sm_70).
        titan_ladder = roofline.load_ladder(ROOT / TITAN_LADDER)
        self.assertEqual(titan_ladder["class_assignment"], ladder["class_assignment"])
        self.assertIn(inputs["devices"]["titan_v"]["demand_ladder_device"], titan_ladder["device"])
        # The L4 is profiled directly: its own demand and L1TEX rate; its clock comes
        # from its LIT-PCBA shape run, since it has no PubChem3D run.
        l4_cal = roofline.ladder_l1tex_calibration(titan_ladder)
        self.assertAlmostEqual(l4_cal["sectors_per_sm_cycle"], 3.82, places=2)
        inputs["devices"]["l4"]["l1tex_sectors_per_sm_cycle"] = l4_cal["sectors_per_sm_cycle"]
        l4_demand = roofline.ladder_demands(titan_ladder)
        with self.assertRaisesRegex(ValueError, "no observed clock"):
            roofline.device_model(roofline.ladder_demands(ladder), inputs, headline, titan,
                                  {"titan_v": l4_demand, "l4": l4_demand})
        model = roofline.device_model(roofline.ladder_demands(ladder), inputs, headline, titan,
                                      {"titan_v": l4_demand, "l4": l4_demand},
                                      {"l4": (1395.0, "LIT-PCBA shape run, q=8")})

        blackwell = model["observations"]["blackwell"]
        volta = model["observations"]["titan_v"]
        self.assertAlmostEqual(blackwell["observed_sm_clock_mhz"], 1807.0)
        self.assertGreater(blackwell["power_cap_fraction"], 0.95)
        self.assertIsNotNone(blackwell["local_linear_power_extrapolation_pair_evaluations_per_s"])
        self.assertEqual(volta["power_cap_fraction"], 0.0)
        self.assertIsNone(volta["local_linear_power_extrapolation_pair_evaluations_per_s"])

        bw_field = model["devices"]["blackwell"]["clock_conditioned_roofs"]["field"]
        bw_analytic = model["devices"]["blackwell"]["clock_conditioned_roofs"]["analytic"]
        self.assertEqual(min(bw_field, key=bw_field.get), "warp_issue")
        self.assertEqual(min(bw_analytic, key=bw_analytic.get), "xu")
        self.assertAlmostEqual(bw_field["warp_issue"] / 1e6, 127.2, places=1)
        titan_run = {row["label"]: row for row in model["large_shape_runs"]}["titan_d5"]
        self.assertAlmostEqual(100 * titan_run["kernel_to_issue_fraction"], 56.1, places=1)
        tv_field = model["devices"]["titan_v"]["clock_conditioned_roofs"]["field"]
        self.assertNotIn("dram", tv_field)
        self.assertEqual(min(tv_field, key=tv_field.get), "l1tex_sectors")
        l4_field = model["devices"]["l4"]["clock_conditioned_roofs"]["field"]
        self.assertEqual(min(l4_field, key=l4_field.get), "l1tex_sectors")
        self.assertAlmostEqual(l4_field["l1tex_sectors"] / 1e6, 27.0, places=1)

    def test_paper_ladder_matches_its_own_work_weighted_summary(self):
        # The ladder file carries the profiler session's own work-weighted figures;
        # the generator's independent computation must reproduce them.
        ladder = roofline.load_ladder(ROOT / LADDER)
        reference = json.loads((ROOT / LADDER).read_text())["work_weighted"]
        demands, model = roofline.ladder_demands(ladder), roofline.ladder_profile_model(ladder)
        for arm in ("field", "analytic"):
            self.assertAlmostEqual(model[f"{arm}_issue_utilization_percent"],
                                   reference[arm]["issue_active_pct"], places=6)
            self.assertAlmostEqual(demands[arm]["warp_instructions_per_evaluation"],
                                   reference[arm]["per_pair_eval"]["warp_instructions"], places=3)
        self.assertGreater(demands["field"]["texture_requests_per_evaluation"], 0)
        self.assertEqual(demands["analytic"]["texture_requests_per_evaluation"], 0.0)



def _ladder(regs=(64.0, 64.0), dram=(100.0, 300.0), weights=(0.25, 0.75), coefficient=0.5):
    """Two points; class A is point p0, class B half p0 and half p1."""
    def point(name, n_real, inst, elapsed, util, reg, dram_bytes):
        arm = lambda scale: {
            "raw": {"sm__inst_executed.sum": inst * scale, "smsp__inst_executed_pipe_xu.sum": 10.0 * scale,
                    "l1tex__t_requests_pipe_tex_mem_texture_op_tex.sum": (20.0 if scale == 1 else 0.0),
                    "l1tex__t_sectors_pipe_tex_mem_texture_op_tex.sum": (320.0 if scale == 1 else 0.0),
                    "dram__bytes_op_read.sum": dram_bytes,
                    "sm__sass_thread_inst_executed_op_fadd_pred_on.sum": 1.0,
                    "sm__sass_thread_inst_executed_op_fmul_pred_on.sum": 1.0,
                    "sm__sass_thread_inst_executed_op_ffma_pred_on.sum": 1.0},
            "elapsed_s": elapsed * scale, "sm_count": 1, "sm_clock_hz": 1.0,
            "utilization": {**{m: util for m in roofline.LADDER_UTILIZATION.values()},
                            "launch__registers_per_thread": reg}}
        return {"point": name, "class": {"L": n_real}, "mean_library_real_atoms": n_real,
                "query_set": "q", "pair_rows": 10, "arms": {"field": arm(1), "analytic": arm(2)}}
    return {"schema": roofline.LADDER_SCHEMA, "device": "test",
            "points": [point("p0", 10, 100.0, 1.0, 80.0, regs[0], dram[0]),
                       point("p1", 30, 300.0, 3.0, 20.0, regs[1], dram[1])],
            "class_assignment": [
                {"class": "A", "pair_eval_weight": weights[0], "points": [{"point": "p0", "coefficient": 1.0}]},
                {"class": "B", "pair_eval_weight": weights[1],
                 "points": [{"point": "p0", "coefficient": coefficient},
                            {"point": "p1", "coefficient": 1.0 - coefficient}]}]}


class PercentPhraseTests(unittest.TestCase):
    def test_one_value_when_all_round_to_one_multiple_of_five_else_range(self):
        self.assertEqual(roofline.percent_phrase((54.9, 56.1)), "about 55")
        self.assertEqual(roofline.percent_phrase((54.9, 58.0)), "55--58")
        self.assertEqual(roofline.percent_phrase((53.0, 52.4)), "52--53")


class LadderTests(unittest.TestCase):
    def load(self, ladder):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ladder-summary.json"
            path.write_text(json.dumps(ladder))
            return roofline.load_ladder(path)

    def test_demands_are_pair_weighted_without_extrapolation(self):
        demands = roofline.ladder_demands(self.load(_ladder()))
        # p0 carries 0.25 + 0.375 = 0.625 of pairs, p1 0.375: 0.625*10 + 0.375*30.
        self.assertAlmostEqual(demands["field"]["warp_instructions_per_evaluation"], 17.5)
        self.assertAlmostEqual(demands["analytic"]["warp_instructions_per_evaluation"], 35.0)
        self.assertAlmostEqual(demands["field"]["dram_read_bytes_per_evaluation"], 0.625 * 10 + 0.375 * 30)
        self.assertEqual([p["point"] for p in demands["per_point"]], ["p0", "p1"])

    def test_utilization_is_time_weighted_and_registers_must_agree(self):
        model = roofline.ladder_profile_model(self.load(_ladder()))
        # time shares: p0 0.625*0.1, p1 0.375*0.3 -> 80% and 20% weighted 0.0625:0.1125.
        self.assertAlmostEqual(model["field_issue_utilization_percent"],
                               (0.0625 * 80 + 0.1125 * 20) / 0.175)
        self.assertEqual(model["field_registers_per_thread"], 64.0)
        self.assertAlmostEqual(model["field_texture_sectors_per_request"], 16.0)
        with self.assertRaises(ValueError):
            roofline.ladder_profile_model(self.load(_ladder(regs=(64.0, 96.0))))

    def test_extent_reports_narrowest_and_widest_point_by_library_atoms(self):
        ladder = _ladder()
        ladder["points"].reverse()
        extent = roofline.ladder_extent(self.load(ladder))
        self.assertEqual((extent["points"], extent["device"]), (2, "test"))
        self.assertEqual((extent["min_library_atoms"], extent["max_library_atoms"]), (10.0, 30.0))
        self.assertEqual(extent["field_issue_percent_narrowest"], 80.0)
        self.assertEqual(extent["field_issue_percent_widest"], 20.0)

    def test_l1tex_rate_is_achieved_over_utilization_weighted_by_time(self):
        cal = roofline.ladder_l1tex_calibration(self.load(_ladder()))
        # p0: 320 sectors / 1 cycle / 0.80 = 400; p1: 320 / 3 / 0.20 = 533.3; time 0.0625:0.1125.
        self.assertAlmostEqual(cal["sectors_per_sm_cycle"], (0.0625 * 400 + 0.1125 * 1600 / 3) / 0.175)
        self.assertAlmostEqual(cal["min_sectors_per_sm_cycle"], 400.0)
        self.assertAlmostEqual(cal["max_sectors_per_sm_cycle"], 1600 / 3)

    def test_unavailable_counter_drops_only_its_roof(self):
        demands = roofline.ladder_demands(self.load(_ladder(dram=(None, 300.0))))
        self.assertIsNone(demands["field"]["dram_read_bytes_per_evaluation"])
        device = {"sms": 1, "warp_schedulers_per_sm": 1, "fp32_lanes_per_sm": 1,
                  "xu_warp_instructions_per_sm_cycle": 1, "dram_bytes_per_s": 1.0,
                  "texture_units_per_sm": 1, "l1tex_sectors_per_sm_cycle": 1}
        roofs = roofline.structural_roofs(demands["field"], device, 1000.0)
        self.assertNotIn("dram", roofs)
        self.assertIn("warp_issue", roofs)

    def test_inconsistent_ladders_are_refused(self):
        for bad in (_ladder(weights=(0.3, 0.8)), _ladder(coefficient=0.7) | {"class_assignment": [
                {"class": "B", "pair_eval_weight": 1.0,
                 "points": [{"point": "p0", "coefficient": 0.7}, {"point": "p1", "coefficient": 0.7}]}]}):
            with self.assertRaises(ValueError):
                self.load(bad)
        missing = _ladder()
        missing["class_assignment"][0]["points"][0]["point"] = "p9"
        with self.assertRaises(ValueError):
            self.load(missing)


if __name__ == "__main__":
    unittest.main()
