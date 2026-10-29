#!/usr/bin/env python3
"""Derive exact semantic work and a declared source-level roofline model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def measured_repeats(report: dict) -> list[dict]:
    repeats = report["screen"]["repeats"]
    expected = int(report["screen"]["timed_repeats_requested"])
    if len(repeats) != expected or any(row.get("phase") != "timed" for row in repeats):
        raise ValueError("run report does not contain its complete measured repeat set")
    return repeats


def derive(report: dict, inputs: dict) -> dict:
    if report["screen"]["mode"] != "shape":
        raise ValueError("the headline model expects a shape run")
    corpus = inputs["corpus"]
    if int(report["corpus"]["conformers"]) != int(corpus["conformers"]):
        raise ValueError("run report and work-model corpus sizes disagree")
    queries = report["query_preparation"]["queries"]
    q_atoms = [int(query["heavy_atoms"]) for query in queries]
    q = len(q_atoms)
    if q != int(report["query_preparation"]["n_queries"]):
        raise ValueError("query list and reported query count disagree")
    b_atoms, a_atoms = int(corpus["real_atoms"]), sum(q_atoms)
    steps = int(inputs["optimizer"]["steps"])
    starts = int(inputs["optimizer"]["starts"])
    passes = starts * (steps + 1)
    if passes != starts * int(inputs["optimizer"]["field_evaluations_per_start"]):
        raise ValueError("optimizer work-model invariants disagree")
    semantic = {
        "optimizer_updates_per_start": steps,
        "field_evaluations_per_start": steps + 1,
        "starts": starts,
        "field_passes_per_pair": passes,
        "query_count": q,
        "query_real_atoms": q_atoms,
        "query_real_atoms_sum": a_atoms,
        "library_conformers": int(corpus["conformers"]),
        "library_real_atoms_sum": b_atoms,
        "conformer_query_pairs": q * int(corpus["conformers"]),
        "analytic_optimizer_shape_gaussian_terms": passes * b_atoms * a_atoms,
        "analytic_optimizer_exp2_calls": passes * b_atoms * a_atoms,
        "field_shape_texture_samples": passes * b_atoms * q,
        "field_exact_rescore_shape_gaussian_terms": b_atoms * a_atoms,
        "field_exact_rescore_exp2_calls": b_atoms * a_atoms,
    }
    acc = inputs["source_level_accounting"]
    analytic_flops = (
        semantic["analytic_optimizer_shape_gaussian_terms"]
        * int(acc["analytic_optimizer_elementary_flops_per_shape_pair_term"])
        + passes * b_atoms * q * int(acc["library_transform_elementary_flops_per_atom"])
    )
    field_flops = (
        semantic["field_shape_texture_samples"]
        * int(acc["field_search_elementary_flops_per_shape_sample"])
        + semantic["field_exact_rescore_shape_gaussian_terms"]
        * int(acc["exact_rescore_elementary_flops_per_shape_pair_term"])
        + b_atoms * q * int(acc["library_transform_elementary_flops_per_atom"])
    )
    uncached_bytes = semantic["field_shape_texture_samples"] * int(acc["half4_node_bytes"]) * int(acc["trilinear_nodes_per_sample"])
    repeats = measured_repeats(report)
    kernel_s = statistics.median(float(row["kernel_s"]) for row in repeats)
    wall_s = statistics.median(float(row["screen_call_wall_s"]) for row in repeats)
    io = None
    if "stored_bytes" in corpus and all("device_stages_s" in row for row in repeats):
        stored_bytes = int(corpus["stored_bytes"])
        h2d_bytes = statistics.median(
            int(row["device_stages_s"]["h2d_bytes"]) for row in repeats)
        h2d_s = statistics.median(
            float(row["device_stages_s"]["h2d_s"]) for row in repeats)
        io = {
            "stored_bytes": stored_bytes,
            "stored_coordinate_bytes": int(corpus["stored_coordinate_bytes"]),
            "decoded_padded_coordinate_bytes": int(corpus["decoded_padded_coordinate_bytes"]),
            "non_coordinate_bytes": int(corpus["non_coordinate_bytes"]),
            "h2d_bytes": h2d_bytes,
            "stored_bytes_per_wall_s": stored_bytes / wall_s,
            "h2d_bytes_per_wall_s": h2d_bytes / wall_s,
            "h2d_bytes_per_active_copy_s": h2d_bytes / h2d_s,
            "h2d_to_stored_byte_ratio": h2d_bytes / stored_bytes,
            "coordinate_decode_ratio": (
                int(corpus["decoded_padded_coordinate_bytes"])
                / int(corpus["stored_coordinate_bytes"])),
            "cache_mode": report["screen"].get("cache_mode"),
        }
    return {
        "schema_version": 1,
        "model_scope": acc["scope_note"],
        "semantic_work": semantic,
        "source_level_work": {
            "convention": acc["convention"],
            "analytic_dominant_loop_elementary_flops": analytic_flops,
            "field_dominant_loop_elementary_flops": field_flops,
            "field_uncached_texture_stencil_bytes": uncached_bytes,
            "warning": "The texture byte count is a no-reuse stencil footprint, not DRAM traffic."
        },
        "measured": {
            "median_kernel_s": kernel_s,
            "median_wall_s": wall_s,
            "field_scalar_texture_samples_per_s": semantic["field_shape_texture_samples"] / kernel_s,
            "field_exact_shape_gaussian_terms_per_s": semantic["field_exact_rescore_shape_gaussian_terms"] / kernel_s
        },
        "representation_shift": {
            "optimizer_gaussian_term_reduction_factor": passes,
            "optimizer_exp2_calls_removed": semantic["analytic_optimizer_exp2_calls"],
            "texture_samples_added": semantic["field_shape_texture_samples"],
            "exact_rescore_exp2_calls_retained": semantic["field_exact_rescore_exp2_calls"]
        },
        "io_accounting": io,
    }


def sci_tex(value: float, digits: int = 3) -> str:
    mantissa, exponent = f"{value:.{digits - 1}e}".split("e")
    return rf"{mantissa}\times 10^{{{int(exponent)}}}"


def constants_tex(model: dict) -> str:
    s, work = model["semantic_work"], model["source_level_work"]
    m, shift = model["measured"], model["representation_shift"]
    lines = [
        "% Generated by scripts/analyze_roofline.py; do not edit.",
        rf"\newcommand{{\RooflineFieldPassesPerPair}}{{{s['field_passes_per_pair']}}}",
        rf"\newcommand{{\DfiveLibraryRealAtoms}}{{{s['library_real_atoms_sum']:,}}}",
        rf"\newcommand{{\DfiveQueryRealAtomsSum}}{{{s['query_real_atoms_sum']}}}",
        rf"\newcommand{{\DfiveFieldTextureSamples}}{{\ensuremath{{{sci_tex(s['field_shape_texture_samples'])}}}}}",
        rf"\newcommand{{\DfiveFieldExactGaussianTerms}}{{\ensuremath{{{sci_tex(s['field_exact_rescore_shape_gaussian_terms'])}}}}}",
        rf"\newcommand{{\DfiveAnalyticOptimizerGaussianTerms}}{{\ensuremath{{{sci_tex(s['analytic_optimizer_shape_gaussian_terms'])}}}}}",
        rf"\newcommand{{\DfiveAnalyticDominantLoopFlops}}{{\ensuremath{{{sci_tex(work['analytic_dominant_loop_elementary_flops'])}}}}}",
        rf"\newcommand{{\DfiveFieldDominantLoopFlops}}{{\ensuremath{{{sci_tex(work['field_dominant_loop_elementary_flops'])}}}}}",
        rf"\newcommand{{\DfiveFieldBillionTextureSamplesPerSecond}}{{{m['field_scalar_texture_samples_per_s']/1e9:.1f}}}",
        rf"\newcommand{{\DfiveFieldBillionExactGaussianTermsPerSecond}}{{{m['field_exact_shape_gaussian_terms_per_s']/1e9:.1f}}}",
        rf"\newcommand{{\FieldOptimizerGaussianReductionFactor}}{{{shift['optimizer_gaussian_term_reduction_factor']}}}",
    ]
    if "profile" in model:
        p = model["profile"]
        lines.extend([
            rf"\newcommand{{\RooflineAnalyticToFieldInstructions}}{{{p['analytic_to_field_instructions']:.2f}}}",
            rf"\newcommand{{\RooflineAnalyticToFieldXuInstructions}}{{{p['analytic_to_field_xu_instructions']:.1f}}}",
            rf"\newcommand{{\RooflineAnalyticRegistersPerThread}}{{{p['analytic_registers_per_thread']:.0f}}}",
            rf"\newcommand{{\RooflineFieldRegistersPerThread}}{{{p['field_registers_per_thread']:.0f}}}",
            rf"\newcommand{{\RooflineAnalyticActiveWarpsPercent}}{{{p['analytic_active_warps_percent']:.1f}}}",
            rf"\newcommand{{\RooflineFieldActiveWarpsPercent}}{{{p['field_active_warps_percent']:.1f}}}",
            rf"\newcommand{{\RooflineAnalyticXuUtilizationPercent}}{{{p['analytic_xu_utilization_percent']:.1f}}}",
            rf"\newcommand{{\RooflineFieldXuUtilizationPercent}}{{{p['field_xu_utilization_percent']:.1f}}}",
            rf"\newcommand{{\RooflineAnalyticLoneTexUtilizationPercent}}{{{p['analytic_l1tex_utilization_percent']:.1f}}}",
            rf"\newcommand{{\RooflineFieldLoneTexUtilizationPercent}}{{{p['field_l1tex_utilization_percent']:.1f}}}",
            rf"\newcommand{{\RooflineFieldTextureSectorsPerRequest}}{{{p['field_texture_sectors_per_request']:.2f}}}",
            rf"\newcommand{{\RooflineFieldIssueUtilizationPercent}}{{{p['field_issue_utilization_percent']:.2f}}}",
            rf"\newcommand{{\RooflineFieldAluUtilizationPercent}}{{{p['field_alu_utilization_percent']:.2f}}}",
            rf"\newcommand{{\RooflineFieldFmaUtilizationPercent}}{{{p['field_fma_utilization_percent']:.2f}}}",
        ])
    if "ladder" in model:
        extent = model["ladder"]
        lines.extend([
            rf"\newcommand{{\RooflineLadderLaunches}}{{{extent['points']}}}",
            rf"\newcommand{{\RooflineLadderMinLibraryAtoms}}{{{extent['min_library_atoms']:.0f}}}",
            rf"\newcommand{{\RooflineLadderMaxLibraryAtoms}}{{{extent['max_library_atoms']:.0f}}}",
            rf"\newcommand{{\RooflineFieldIssueNarrowestPercent}}{{{extent['field_issue_percent_narrowest']:.1f}}}",
            rf"\newcommand{{\RooflineFieldIssueWidestPercent}}{{{extent['field_issue_percent_widest']:.1f}}}",
        ])
    if "l1tex_calibration" in model:
        cal = model["l1tex_calibration"]
        lines.extend([
            rf"\newcommand{{\RooflineBlackwellLoneTexSectorsPerSmCycle}}{{{cal['sectors_per_sm_cycle']:.2f}}}",
            rf"\newcommand{{\RooflineBlackwellLoneTexSectorsPerSmCycleMin}}{{{cal['min_sectors_per_sm_cycle']:.2f}}}",
            rf"\newcommand{{\RooflineBlackwellLoneTexSectorsPerSmCycleMax}}{{{cal['max_sectors_per_sm_cycle']:.2f}}}",
        ])
    if model.get("io_accounting"):
        io_model = model["io_accounting"]
        lines.extend([
            rf"\newcommand{{\PubchemStoredGigabytes}}{{{io_model['stored_bytes']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemStoredCoordinateGigabytes}}{{{io_model['stored_coordinate_bytes']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemDecodedCoordinateGigabytes}}{{{io_model['decoded_padded_coordinate_bytes']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemNonCoordinateGigabytes}}{{{io_model['non_coordinate_bytes']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemHtwoDTransferredGigabytes}}{{{io_model['h2d_bytes']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemStoredGigabytesPerSecond}}{{{io_model['stored_bytes_per_wall_s']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemHtwoDWholeRunGigabytesPerSecond}}{{{io_model['h2d_bytes_per_wall_s']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemHtwoDActiveGigabytesPerSecond}}{{{io_model['h2d_bytes_per_active_copy_s']/1e9:.2f}}}",
            rf"\newcommand{{\PubchemHtwoDToStoredByteRatio}}{{{io_model['h2d_to_stored_byte_ratio']:.2f}}}",
            rf"\newcommand{{\PubchemCoordinateDecodeRatio}}{{{io_model['coordinate_decode_ratio']:.2f}}}",
        ])
    if "device_model" in model:
        d = model["device_model"]
        blackwell, titan = d["observations"]["blackwell"], d["observations"]["titan_v"]
        bw_caps = d["devices"]["blackwell"]["clock_conditioned_roofs"]
        tv_caps = d["devices"]["titan_v"]["clock_conditioned_roofs"]
        demand = d["ladder_demands"]
        large = {row["label"]: row for row in d["large_shape_runs"]}
        # The bottleneck prose names issue as GB202's field limit and L1TEX as GV100's.
        binding = {key: d["devices"][key]["limiting_structural_resource"]["field"]
                   for key in ("blackwell", "l4", "titan_v")}
        if binding != {"blackwell": "warp_issue", "l4": "l1tex_sectors", "titan_v": "l1tex_sectors"}:
            raise ValueError(f"field-kernel binding resources changed ({binding}); revise the bottleneck prose")
        l4_caps = d["devices"]["l4"]["clock_conditioned_roofs"]
        cal = model["l4_l1tex_calibration"]
        specs = model["device_specs"]
        lines.extend([
            rf"\newcommand{{\RooflineLFourFieldIssueMillionPairsPerSecond}}{{{l4_caps['field']['warp_issue']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineLFourFieldLoneTexMillionPairsPerSecond}}{{{l4_caps['field']['l1tex_sectors']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineLFourAnalyticStructuralMillionPairsPerSecond}}{{{min(l4_caps['analytic'].values())/1e6:.1f}}}",
            rf"\newcommand{{\RooflineLFourObservedClockMHz}}{{{d['devices']['l4']['observed_sm_clock_mhz']:.0f}}}",
            rf"\newcommand{{\RooflineLFourLoneTexSectorsPerSmCycle}}{{{cal['sectors_per_sm_cycle']:.2f}}}",
            rf"\newcommand{{\RooflineLFourLoneTexSectorsPerSmCycleMin}}{{{cal['min_sectors_per_sm_cycle']:.2f}}}",
            rf"\newcommand{{\RooflineLFourLoneTexSectorsPerSmCycleMax}}{{{cal['max_sectors_per_sm_cycle']:.2f}}}",
        ])
        for key, stem in (("blackwell", "Blackwell"), ("l4", "LFour"), ("titan_v", "Titan")):
            spec = specs[key]
            lines.extend([
                rf"\newcommand{{\Roofline{stem}Sms}}{{{spec['sms']}}}",
                rf"\newcommand{{\Roofline{stem}FpLanesPerSm}}{{{spec['fp32_lanes_per_sm']}}}",
                rf"\newcommand{{\Roofline{stem}DramGigabytesPerSecond}}{{{spec['dram_bytes_per_s']/1e9:g}}}",
                rf"\newcommand{{\Roofline{stem}SpecifiedMaxClockGHz}}{{{spec['specified_max_clock_mhz']/1000:g}}}",
                rf"\newcommand{{\Roofline{stem}PowerLimitW}}{{{spec['power_limit_w']:g}}}",
            ])
        xu = {spec["xu_warp_instructions_per_sm_cycle"] for spec in specs.values()}
        if len(xu) != 1:
            raise ValueError("the prose states one XU rate for every device")
        lines.append(rf"\newcommand{{\RooflineXuWarpInstructionsPerSmCycle}}{{{xu.pop():g}}}")
        kernel_to_structural = (
            100 * blackwell["kernel_pair_evaluations_per_s"] / min(bw_caps["field"].values()),
            100 * large["titan_d5"]["kernel_to_issue_fraction"])
        lines.extend([
            rf"\newcommand{{\RooflineBlackwellObservedClockMHz}}{{{blackwell['observed_sm_clock_mhz']:.0f}}}",
            rf"\newcommand{{\RooflineTitanObservedClockMHz}}{{{titan['observed_sm_clock_mhz']:.0f}}}",
            rf"\newcommand{{\RooflineBlackwellClockFractionPercent}}{{{100*d['devices']['blackwell']['observed_to_max_clock_fraction']:.1f}}}",
            rf"\newcommand{{\RooflineTitanClockFractionPercent}}{{{100*d['devices']['titan_v']['observed_to_max_clock_fraction']:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellKernelMillionPairsPerSecond}}{{{blackwell['kernel_pair_evaluations_per_s']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineTitanKernelMillionPairsPerSecond}}{{{titan['kernel_pair_evaluations_per_s']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellMeanPowerW}}{{{blackwell['mean_power_w']:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellMaximumPowerW}}{{{blackwell['maximum_sampled_power_w']:.1f}}}",
            rf"\newcommand{{\RooflineTitanMeanPowerW}}{{{titan['mean_power_w']:.1f}}}",
            rf"\newcommand{{\RooflineTitanMaximumPowerW}}{{{titan['maximum_sampled_power_w']:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellPowerCapPercent}}{{{100*blackwell['power_cap_fraction']:.1f}}}",
            rf"\newcommand{{\RooflineTitanPowerCapPercent}}{{{100*titan['power_cap_fraction']:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellLocalPowerExtrapolatedMillionPairsPerSecond}}{{{blackwell['local_linear_power_extrapolation_pair_evaluations_per_s']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellFieldStructuralMillionPairsPerSecond}}{{{min(bw_caps['field'].values())/1e6:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellMaxClockIssueMillionPairsPerSecond}}{{{bw_caps['field']['warp_issue']/d['devices']['blackwell']['observed_to_max_clock_fraction']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellKernelToStructuralPercent}}{{{100*blackwell['kernel_pair_evaluations_per_s']/min(bw_caps['field'].values()):.1f}}}",
            rf"\newcommand{{\RooflineBlackwellWallToStructuralPercent}}{{{100*blackwell['wall_pair_evaluations_per_s']/min(bw_caps['field'].values()):.1f}}}",
            rf"\newcommand{{\RooflineBlackwellKernelToPowerExtrapolatedPercent}}{{{100*blackwell['kernel_pair_evaluations_per_s']/blackwell['local_linear_power_extrapolation_pair_evaluations_per_s']:.1f}}}",
            rf"\newcommand{{\RooflineTitanKernelToStructuralPercent}}{{{100*large['titan_d5']['kernel_to_issue_fraction']:.1f}}}",
            rf"\newcommand{{\RooflineTitanWallToStructuralPercent}}{{{100*large['titan_d5']['wall_to_issue_fraction']:.1f}}}",
            # The abstract's "% of peak": one value when both devices round alike, else the range.
            rf"\newcommand{{\RooflineKernelToStructuralPercentPhrase}}{{{percent_phrase(kernel_to_structural)}}}",
            rf"\newcommand{{\RooflineBlackwellFieldIssueMillionPairsPerSecond}}{{{bw_caps['field']['warp_issue']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineBlackwellFieldLoneTexMillionPairsPerSecond}}{{{bw_caps['field']['l1tex_sectors']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineTitanFieldIssueMillionPairsPerSecond}}{{{tv_caps['field']['warp_issue']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineTitanFieldLoneTexMillionPairsPerSecond}}{{{tv_caps['field']['l1tex_sectors']/1e6:.1f}}}",
            rf"\newcommand{{\RooflineTitanLoneTexSectorsPerSmCycle}}{{{d['devices']['titan_v']['l1tex_sectors_per_sm_cycle']:g}}}",
            rf"\newcommand{{\RooflineDfiveIssueBoundRatio}}{{{large['blackwell_d5']['issue_upper_bound_pair_evaluations_per_s']/large['titan_d5']['issue_upper_bound_pair_evaluations_per_s']:.2f}}}",
            rf"\newcommand{{\RooflineDfiveKernelSpeedRatio}}{{{blackwell['kernel_pair_evaluations_per_s']/titan['kernel_pair_evaluations_per_s']:.2f}}}",
            rf"\newcommand{{\RooflineDfiveWallSpeedRatio}}{{{blackwell['wall_pair_evaluations_per_s']/titan['wall_pair_evaluations_per_s']:.2f}}}",
            rf"\newcommand{{\RooflineDfiveFpBoundRatio}}{{{bw_caps['field']['fp32']/tv_caps['field']['fp32']:.2f}}}",
            rf"\newcommand{{\RooflineBlackwellAnalyticStructuralMillionPairsPerSecond}}{{{min(bw_caps['analytic'].values())/1e6:.1f}}}",
            rf"\newcommand{{\RooflineTitanFieldStructuralMillionPairsPerSecond}}{{{min(tv_caps['field'].values())/1e6:.1f}}}",
            rf"\newcommand{{\RooflineTitanAnalyticStructuralMillionPairsPerSecond}}{{{min(tv_caps['analytic'].values())/1e6:.1f}}}",
            rf"\newcommand{{\RooflineDfiveMeanLibraryAtoms}}{{{demand['d5_mean_library_real_atoms']:.2f}}}",
            rf"\newcommand{{\RooflineFieldWarpInstructionsPerPair}}{{{demand['field']['warp_instructions_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineAnalyticWarpInstructionsPerPair}}{{{demand['analytic']['warp_instructions_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineFieldFpFlopsPerPair}}{{{demand['field']['fp32_flops_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineAnalyticFpFlopsPerPair}}{{{demand['analytic']['fp32_flops_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineFieldXuInstructionsPerPair}}{{{demand['field']['xu_warp_instructions_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineAnalyticXuInstructionsPerPair}}{{{demand['analytic']['xu_warp_instructions_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineFieldTextureRequestsPerPair}}{{{demand['field']['texture_requests_per_evaluation']:,.0f}}}",
            rf"\newcommand{{\RooflineFieldTextureSectorsPerPair}}{{{demand['field']['texture_sectors_per_evaluation']:,.0f}}}",
        ])
    lines.append("")
    return "\n".join(lines)


def table_tex() -> str:
    return r"""% Generated by scripts/analyze_roofline.py; do not edit.
\begin{table}[t]
  \centering
  \small
  \caption{Modeled work for the four-query PubChem3D shape screen. Counts are exact
  semantic operations for the production step/start configuration; they do not
  assign a FLOP equivalent to texture interpolation or \texttt{exp2}.}
  \label{tab:roofline-work}
  \begin{tabular}{@{}lrr@{}}
    \toprule
    Resource demand & direct analytic & field + exact cascade \\
    \midrule
    Optimizer Gaussian/\texttt{exp2} terms & \DfiveAnalyticOptimizerGaussianTerms{} & 0 \\
    Exact-cascade Gaussian/\texttt{exp2} terms & 0 & \DfiveFieldExactGaussianTerms{} \\
    Candidate \texttt{float4} texture lookups & 0 & \DfiveFieldTextureSamples{} \\
    Accounted elementary loop FLOPs & \DfiveAnalyticDominantLoopFlops{} & \DfiveFieldDominantLoopFlops{} \\
    \bottomrule
  \end{tabular}
\end{table}
"""


def run_observation(report: dict, power_limit_w: float,
                    workload_name: str | None = None) -> dict:
    """Summarize benchmark timing and telemetry without mixing repeat phases."""
    repeats = measured_repeats(report)
    pairs = int(repeats[0]["conformer_pairs_screened"])
    if any(int(row["conformer_pairs_screened"]) != pairs for row in repeats):
        raise ValueError("pair count differs across measured repeats")

    def med(path: tuple[str, ...]) -> float:
        values = []
        for row in repeats:
            value = row
            for key in path:
                value = value[key]
            values.append(float(value))
        return statistics.median(values)

    kernel_s = med(("kernel_s",))
    wall_s = med(("screen_call_wall_s",))
    h2d_s = med(("device_stages_s", "h2d_s"))
    topk_s = med(("device_stages_s", "topk_s"))
    mean_power_w = med(("telemetry", "power_draw_w", "mean"))
    cap_fraction = med(("telemetry", "sw_power_cap_fraction"))
    kernel_rate = pairs / kernel_s
    power_extrapolation = None
    if cap_fraction > 0.5:
        # This is a local tangent estimate, not a claim of globally linear
        # throughput with power.  It is intentionally reported only when the
        # hardware says the software power limiter was active.
        power_extrapolation = kernel_rate * power_limit_w / mean_power_w
    return {
        "workload": f"{workload_name or report['corpus']['name']}, q={report['query_preparation']['n_queries']}",
        "pairs": pairs,
        "median_kernel_s": kernel_s,
        "median_wall_s": wall_s,
        "kernel_pair_evaluations_per_s": kernel_rate,
        "wall_pair_evaluations_per_s": pairs / wall_s,
        "h2d_pair_evaluations_per_s": pairs / h2d_s,
        "topk_pair_evaluations_per_s": pairs / topk_s,
        "observed_sm_clock_mhz": med(("telemetry", "achieved_clock_mhz", "median")),
        "mean_power_w": mean_power_w,
        "maximum_sampled_power_w": max(float(row["telemetry"]["power_draw_w"]["max"]) for row in repeats),
        "power_limit_w": power_limit_w,
        "power_cap_fraction": cap_fraction,
        "local_linear_power_extrapolation_pair_evaluations_per_s": power_extrapolation,
    }


LADDER_SCHEMA = "t300.roofline-ladder.v1"
LADDER_COUNTS = {
    "warp_instructions_per_evaluation": ("sm__inst_executed.sum",),
    "xu_warp_instructions_per_evaluation": ("smsp__inst_executed_pipe_xu.sum",),
    "texture_requests_per_evaluation": ("l1tex__t_requests_pipe_tex_mem_texture_op_tex.sum",),
    "texture_sectors_per_evaluation": ("l1tex__t_sectors_pipe_tex_mem_texture_op_tex.sum",),
    "dram_read_bytes_per_evaluation": ("dram__bytes_op_read.sum",),
}
LADDER_UTILIZATION = {
    "active_warps_percent": "smsp__warps_active.avg.pct_of_peak_sustained_active",
    "issue_utilization_percent": "smsp__issue_active.avg.pct_of_peak_sustained_active",
    "xu_utilization_percent": "sm__inst_executed_pipe_xu.avg.pct_of_peak_sustained_active",
    "l1tex_utilization_percent": "l1tex__throughput.avg.pct_of_peak_sustained_active",
    "alu_utilization_percent": "sm__pipe_alu_cycles_active.avg.pct_of_peak_sustained_active",
    "fma_utilization_percent": "sm__pipe_fma_cycles_active.avg.pct_of_peak_sustained_active",
}


def load_ladder(path: Path) -> dict:
    """A profile ladder: one Nsight launch per D5 launch-width class, with D5's
    pair-evaluation weight for each class and how each class maps onto points.
    Refuses a ladder whose weights or coefficients do not each sum to one, whose
    classes cite missing points, or whose points used different queries."""
    ladder = json.loads(Path(path).read_text(encoding="utf-8"))
    if ladder.get("schema") != LADDER_SCHEMA:
        raise ValueError(f"{path}: not a {LADDER_SCHEMA} ladder")
    points = {p["point"]: p for p in ladder["points"]}
    if len({p["query_set"] for p in points.values()}) != 1:
        raise ValueError("ladder points used different query sets")
    weights = 0.0
    for entry in ladder["class_assignment"]:
        weights += float(entry["pair_eval_weight"])
        coefficients = sum(float(c["coefficient"]) for c in entry["points"])
        if abs(coefficients - 1.0) > 1e-9:
            raise ValueError(f"class {entry['class']}: point coefficients sum to {coefficients}")
        for c in entry["points"]:
            if c["point"] not in points:
                raise ValueError(f"class {entry['class']} cites missing point {c['point']}")
    if abs(weights - 1.0) > 1e-9:
        raise ValueError(f"D5 class weights sum to {weights}")
    return ladder


def _point_weights(ladder: dict) -> dict[str, float]:
    """Each point's share of D5 pair evaluations, after class interpolation."""
    share: dict[str, float] = {}
    for entry in ladder["class_assignment"]:
        for c in entry["points"]:
            share[c["point"]] = share.get(c["point"], 0.0) + (
                float(entry["pair_eval_weight"]) * float(c["coefficient"]))
    return share


def _per_pair(point: dict, arm: str) -> dict:
    raw, rows = point["arms"][arm]["raw"], float(point["pair_rows"])
    out = {}
    for key, (metric,) in LADDER_COUNTS.items():
        value = raw.get(metric)
        out[key] = None if value is None else float(value) / rows
    out["fp32_flops_per_evaluation"] = (
        float(raw["sm__sass_thread_inst_executed_op_fadd_pred_on.sum"])
        + float(raw["sm__sass_thread_inst_executed_op_fmul_pred_on.sum"])
        + 2.0 * float(raw["sm__sass_thread_inst_executed_op_ffma_pred_on.sum"])) / rows
    out["elapsed_s_per_evaluation"] = float(point["arms"][arm]["elapsed_s"]) / rows
    return out


def ladder_demands(ladder: dict) -> dict:
    """D5-average per-pair demand: each count is the pair-work-weighted mean of
    the ladder's per-pair counts, so no launch width is extrapolated. A count
    unavailable at any point (DRAM on AD104) is None for the whole ladder."""
    share = _point_weights(ladder)
    points = {p["point"]: p for p in ladder["points"]}
    out = {"device": ladder["device"], "per_point": []}
    for arm in ("field", "analytic"):
        rows = {name: _per_pair(points[name], arm) for name in share}
        demand = {}
        for key in next(iter(rows.values())):
            values = [rows[name][key] for name in share]
            demand[key] = (None if any(v is None for v in values)
                           else sum(share[name] * rows[name][key] for name in share))
        out[arm] = demand
    for name in sorted(share):
        point = points[name]
        out["per_point"].append({
            "point": name, "class": point["class"],
            "mean_library_real_atoms": float(point["mean_library_real_atoms"]),
            "d5_pair_share": share[name],
            "field": _per_pair(point, "field"), "analytic": _per_pair(point, "analytic")})
    return out


def ladder_extent(ladder: dict) -> dict:
    """What the ladder covers: its launches, their library atom range, and the
    field kernel's issue utilization at the narrowest and widest launch."""
    points = sorted(ladder["points"], key=lambda p: float(p["mean_library_real_atoms"]))
    issue = "smsp__issue_active.avg.pct_of_peak_sustained_active"
    return {
        "points": len(points),
        "min_library_atoms": float(points[0]["mean_library_real_atoms"]),
        "max_library_atoms": float(points[-1]["mean_library_real_atoms"]),
        "field_issue_percent_narrowest": float(points[0]["arms"]["field"]["utilization"][issue]),
        "field_issue_percent_widest": float(points[-1]["arms"]["field"]["utilization"][issue]),
        "device": ladder["device"],
    }


def ladder_profile_model(ladder: dict) -> dict:
    """The profile-model figures over the ladder. Utilization percentages are
    weighted by the time D5's pairs spend at each point (pair share x profiled
    time per pair); register counts must be the same at every point."""
    share = _point_weights(ladder)
    points = {p["point"]: p for p in ladder["points"]}
    model = {}
    for arm in ("field", "analytic"):
        time = {n: share[n] * float(points[n]["arms"][arm]["elapsed_s"]) / float(points[n]["pair_rows"])
                for n in share}
        total = sum(time.values())
        for key, metric in LADDER_UTILIZATION.items():
            model[f"{arm}_{key}"] = sum(
                time[n] * float(points[n]["arms"][arm]["utilization"][metric]) for n in share) / total
        registers = {float(points[n]["arms"][arm]["utilization"]["launch__registers_per_thread"])
                     for n in share}
        if len(registers) != 1:
            raise ValueError(f"{arm} registers per thread vary across the ladder: {sorted(registers)}")
        model[f"{arm}_registers_per_thread"] = registers.pop()
    demands = ladder_demands(ladder)
    field, analytic = demands["field"], demands["analytic"]
    if not field["texture_requests_per_evaluation"] or analytic["texture_requests_per_evaluation"]:
        raise ValueError("ladder does not distinguish the field and analytic texture paths")
    model["analytic_to_field_instructions"] = (analytic["warp_instructions_per_evaluation"]
                                               / field["warp_instructions_per_evaluation"])
    model["analytic_to_field_xu_instructions"] = (analytic["xu_warp_instructions_per_evaluation"]
                                                  / field["xu_warp_instructions_per_evaluation"])
    model["field_texture_sectors_per_request"] = (field["texture_sectors_per_evaluation"]
                                                  / field["texture_requests_per_evaluation"])
    return model


def percent_phrase(values) -> str:
    """'about N' when every value rounds to the same multiple of 5 (N), else the
    whole-percent range 'min--max'."""
    fives = {5 * math.floor(v / 5 + 0.5) for v in values}
    if len(fives) == 1:
        return f"about {fives.pop()}"
    return f"{math.floor(min(values) + 0.5)}--{math.floor(max(values) + 0.5)}"


def ladder_l1tex_calibration(ladder: dict) -> dict:
    """The profiled device's effective L1TEX texture-sector rate per SM-cycle.
    At each point the field kernel's achieved sectors/SM/cycle is divided by its
    L1TEX utilization; the points are weighted by time, as in ladder_profile_model."""
    share = _point_weights(ladder)
    points = {p["point"]: p for p in ladder["points"]}
    rates, time = {}, {}
    for n in share:
        arm = points[n]["arms"]["field"]
        cycles = float(arm["sm_count"]) * float(arm["elapsed_s"]) * float(arm["sm_clock_hz"])
        achieved = float(arm["raw"]["l1tex__t_sectors_pipe_tex_mem_texture_op_tex.sum"]) / cycles
        rates[n] = achieved / (float(arm["utilization"][LADDER_UTILIZATION["l1tex_utilization_percent"]]) / 100)
        time[n] = share[n] * float(arm["elapsed_s"]) / float(points[n]["pair_rows"])
    total = sum(time.values())
    return {"sectors_per_sm_cycle": sum(time[n] * rates[n] for n in share) / total,
            "min_sectors_per_sm_cycle": min(rates.values()),
            "max_sectors_per_sm_cycle": max(rates.values())}


def structural_roofs(demand: dict, device: dict, clock_mhz: float) -> dict:
    """Clock-conditioned per-resource ceilings in pair evaluations/s."""
    hz = clock_mhz * 1e6
    sm = float(device["sms"])
    roofs = {
        "warp_issue": sm * device["warp_schedulers_per_sm"] * hz / demand["warp_instructions_per_evaluation"],
        "fp32": sm * device["fp32_lanes_per_sm"] * 2.0 * hz / demand["fp32_flops_per_evaluation"],
        "xu": sm * device["xu_warp_instructions_per_sm_cycle"] * hz / demand["xu_warp_instructions_per_evaluation"],
    }
    if demand.get("dram_read_bytes_per_evaluation"):  # None where the counter is unavailable
        roofs["dram"] = device["dram_bytes_per_s"] / demand["dram_read_bytes_per_evaluation"]
    if demand["texture_requests_per_evaluation"] > 0:
        roofs["texture_issue"] = sm * device["texture_units_per_sm"] * hz / demand["texture_requests_per_evaluation"]
        roofs["l1tex_sectors"] = sm * device["l1tex_sectors_per_sm_cycle"] * hz / demand["texture_sectors_per_evaluation"]
    return roofs


def scale_demand(demand: dict, factor: float) -> dict:
    return {key: value * factor for key, value in demand.items()}


def device_model(demands: dict, inputs: dict,
                 blackwell_report: dict, titan_report: dict,
                 device_demands: dict | None = None, clocks: dict | None = None) -> dict:
    """Clock-conditioned roofs for each device from ladder_demands' per-pair demands.
    device_demands overrides the demand for a device whose build's instruction
    stream another ladder matches better (the GV100 projection uses sm_89's).
    clocks gives the observed SM clock of a device with no PubChem3D run."""
    per_device = {key: (device_demands or {}).get(key, demands) for key in inputs["devices"]}
    observations = {
        "blackwell": run_observation(
            blackwell_report, inputs["devices"]["blackwell"]["power_limit_w"],
            workload_name=inputs["corpus"]["name"]),
        "titan_v": run_observation(
            titan_report, inputs["devices"]["titan_v"]["power_limit_w"],
            workload_name=inputs["corpus"]["name"]),
    }
    devices = {}
    for key, device in inputs["devices"].items():
        if device.get("l1tex_sectors_per_sm_cycle") is None:
            raise ValueError(f"{key}: L1TEX sectors/SM/cycle is not calibrated (pass --ladder)")
        if key in observations:
            clock, clock_source = observations[key]["observed_sm_clock_mhz"], "PubChem3D shape run"
        elif key in (clocks or {}):
            clock, clock_source = clocks[key]
        else:
            raise ValueError(f"{key}: no observed clock (no run and no --l4-clock-run)")
        arm_roofs = {arm: structural_roofs(per_device[key][arm], device, clock)
                     for arm in ("field", "analytic")}
        devices[key] = {
            "label": device["label"],
            "chip": device["chip"],
            "observed_sm_clock_mhz": clock,
            "specified_max_clock_mhz": device["specified_max_clock_mhz"],
            "observed_to_max_clock_fraction": clock / device["specified_max_clock_mhz"],
            "clock_conditioned_roofs": arm_roofs,
            "limiting_structural_resource": {
                arm: min(arm_roofs[arm], key=arm_roofs[arm].get)
                for arm in ("field", "analytic")
            },
            "basis": device["basis"],
            "l1tex_sectors_per_sm_cycle": device["l1tex_sectors_per_sm_cycle"],
            "demand_source": device.get("demand_source", "profiled device's ladder"),
            "clock_source": clock_source,
        }
    large_runs = []

    def add_run(label: str, corpus: str, device_key: str, observation: dict,
                field_demand: dict) -> None:
        issue_roof = structural_roofs(
            field_demand, inputs["devices"][device_key],
            observation["observed_sm_clock_mhz"])["warp_issue"]
        large_runs.append({
            "label": label,
            "corpus": corpus,
            "device": device_key,
            "device_label": inputs["devices"][device_key]["label"],
            "observation": observation,
            "issue_upper_bound_pair_evaluations_per_s": issue_roof,
            "kernel_to_issue_fraction": observation["kernel_pair_evaluations_per_s"] / issue_roof,
            "wall_to_issue_fraction": observation["wall_pair_evaluations_per_s"] / issue_roof,
        })

    add_run("blackwell_d5", "PubChem3D", "blackwell", observations["blackwell"], per_device["blackwell"]["field"])
    add_run("titan_d5", "PubChem3D", "titan_v", observations["titan_v"], per_device["titan_v"]["field"])

    return {"ladder_demands": demands,
            "device_demands": {key: per_device[key] for key in (device_demands or {})},
            "devices": devices,
            "observations": observations, "large_shape_runs": large_runs}


def rate_cell(value: float, bold: bool = False) -> str:
    rendered = f"{value / 1e6:,.1f}"
    return rf"\textbf{{{rendered}}}" if bold else rendered


def caps_cell(value: float, bold: bool = False) -> str:
    """One decimal below 100 million pairs/s, whole numbers at or above it."""
    millions = value / 1e6
    rendered = f"{millions:,.1f}" if millions < 100 else f"{millions:,.0f}"
    return rf"\textbf{{{rendered}}}" if bold else rendered


def device_caps_table(model: dict) -> str:
    devices = model["devices"]
    resources = [
        ("warp_issue", "all-instruction issue"),
        ("l1tex_sectors", "L1TEX sector service"),
        ("fp32", "FP32 arithmetic lanes"),
        ("xu", "special-function/XU issue"),
        ("texture_issue", "texture-request issue"),
        ("dram", "device DRAM reads"),
    ]
    lines = [
        "% Generated by scripts/analyze_roofline.py; do not edit.",
        r"\begin{table}[b]",
        r"  \centering",
        r"  \small",
        r"  \caption{Roofline model: maximum achievable alignment rate, in million PubChem3D-average pairs/s, if throughput were limited by only the specified resource. Roofline is computed at observed median clocks for each card (AD104's from its LIT-PCBA shape run, as the L4 has no PubChem3D run). GB202 and AD104 use their own profiled instruction demand; GV100 projects the AD104 (sm\_89) stream, whose field loop compiles as on sm\_70. Bold marks the binding ceiling for each kernel / chip.}",
        r"  \label{tab:roofline-device-caps}",
        r"  \begin{tabular}{@{}lrrrrrr@{}}",
        r"    \toprule",
        r"    & \multicolumn{3}{c}{Max Field Mpair/s} & \multicolumn{3}{c}{Max Analytic Mpair/s} \\",
        r"    Resource & GB202 & AD104 & GV100 & GB202 & AD104 & GV100 \\",
        r"    \midrule",
    ]
    for resource, label in resources:
        cells = []
        for arm in ("field", "analytic"):
            for device_key in ("blackwell", "l4", "titan_v"):
                device = devices[device_key]
                roofs = device["clock_conditioned_roofs"][arm]
                if resource not in roofs:
                    cells.append(r"--")
                else:
                    cells.append(caps_cell(roofs[resource], device["limiting_structural_resource"][arm] == resource))
        lines.append(f"    {label} & " + " & ".join(cells) + r" \\")
    lines.extend([r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""])
    return "\n".join(lines)


def observed_table(model: dict) -> str:
    obs = model["observations"]
    lines = [
        "% Generated by scripts/analyze_roofline.py; do not edit.",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \small",
        r"  \caption{Observed matched PubChem3D shape-screen operating points, including the effective result of power management and execution stalls. Each row contains 2.050 billion pair evaluations. H2D and top-$k$ columns divide pair count by isolated device-stage time.}",
        r"  \label{tab:roofline-observed}",
        r"  \begin{tabular}{@{}lrrrrrr@{}}",
        r"    \toprule",
        r"    Device & clock & kernel & wall & H2D & top-$k$ & power cap \\",
        r"    & (MHz) & \multicolumn{4}{c}{million pair evaluations/s} & (\% samples) \\",
        r"    \midrule",
    ]
    for key in ("blackwell", "titan_v"):
        row = obs[key]
        lines.append(
            f"    {model['devices'][key]['label']} & {row['observed_sm_clock_mhz']:.0f} & "
            f"{row['kernel_pair_evaluations_per_s']/1e6:.1f} & {row['wall_pair_evaluations_per_s']/1e6:.1f} & "
            f"{row['h2d_pair_evaluations_per_s']/1e6:.1f} & {row['topk_pair_evaluations_per_s']/1e6:.1f} & "
            f"{100*row['power_cap_fraction']:.1f}" + r" \\")
    lines.extend([r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""])
    return "\n".join(lines)


SCALE_TABLE_GPU_NAMES = {"blackwell": "RTX PRO 6000 Blackwell", "titan_v": "TITAN V"}


def scale_roofline_table(model: dict) -> str:
    runs = [item for item in model["large_shape_runs"] if item["corpus"] == "PubChem3D"]
    if [item["device"] for item in runs] != ["blackwell", "titan_v"]:
        raise ValueError("scale table expects one PubChem3D run per GPU, Blackwell first")
    pair_counts = {item["observation"]["pairs"] for item in runs}
    if len(pair_counts) != 1:
        raise ValueError("PubChem3D runs in the scale table differ in pair count")
    pairs = pair_counts.pop()
    mantissa, exponent = f"{pairs:.3e}".split("e")
    rows = []
    for item in runs:
        observation = item["observation"]
        rows.append(
            f"    {SCALE_TABLE_GPU_NAMES[item['device']]} & "
            f"{observation['wall_pair_evaluations_per_s']/1e6:.2f} & "
            f"{observation['kernel_pair_evaluations_per_s']/1e6:.2f} & "
            f"{item['issue_upper_bound_pair_evaluations_per_s']/1e6:.1f} & "
            f"{100*item['kernel_to_issue_fraction']:.1f}\\%" + r" \\")
    return "\n".join([
        "% Generated by scripts/analyze_roofline.py; do not edit.",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \small",
        r"  \caption{ROSHAMBO3 kernel efficiency. Measurements were taken from shape screens of",
        rf"  PubChem3D (${float(mantissa):.3f}\times10^{{{int(exponent)}}}$ conformer-pairs). We report the screening rate by wall-clock time and kernel-only time,",
        r"  using the latter against the roofline model to estimate efficiency. Nsight profiling was unavailable for TITAN V; its instruction mix is modeled on the one measured on an L4 (sm\_89), whose field loop compiles as on sm\_70.}",
        r"  \label{tab:scale-roofline}",
        r"  \begin{tabular}{@{}lrrrr@{}}",
        r"    \toprule",
        r"        & Mpair/s   & Mpair/s     & Mpair/s  & Percent of \\",
        r"    GPU & wall-time & kernel time & roofline & theoretical peak \\",
        r"    \midrule",
        *rows,
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path)
    parser.add_argument("--inputs", type=Path, default=Path("data/roofline-work-model.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--titan-run", type=Path)
    parser.add_argument("--ladder", type=Path, help="profile ladder (ladder-summary.json)")
    parser.add_argument("--l4-ladder", type=Path,
                        help="the L4 (sm_89) ladder: the L4's own demand and L1TEX rate, and the GV100 projection's demand")
    parser.add_argument("--l4-clock-run", type=Path,
                        help="an L4 shape run whose telemetry gives its observed clock")
    args = parser.parse_args()
    if args.run is None:
        parser.error("--run is required")
    model = derive(json.loads(args.run.read_text()), json.loads(args.inputs.read_text()))
    sources = [args.run, args.inputs]
    inputs = json.loads(args.inputs.read_text())
    demands = None
    if args.ladder is not None:
        ladder = load_ladder(args.ladder)
        model["profile"] = ladder_profile_model(ladder)
        demands = ladder_demands(ladder)
        model["ladder"] = ladder_extent(ladder)
        # The profiled device's L1TEX rate comes from the ladder, not from the work model.
        model["l1tex_calibration"] = ladder_l1tex_calibration(ladder)
        calibrated = [d for d in inputs["devices"].values()
                      if d.get("l1tex_sectors_per_sm_cycle_source") == "ladder"]
        if len(calibrated) != 1 or calibrated[0]["label"] not in ladder["device"]:
            raise ValueError("the ladder must calibrate exactly the device it profiled")
        calibrated[0]["l1tex_sectors_per_sm_cycle"] = model["l1tex_calibration"]["sectors_per_sm_cycle"]
        semantic = model["semantic_work"]
        demands["d5_mean_library_real_atoms"] = (semantic["library_real_atoms_sum"]
                                                 / semantic["library_conformers"])
        sources.append(args.ladder)
    model["device_specs"] = {key: {name: device[name] for name in (
        "sms", "fp32_lanes_per_sm", "dram_bytes_per_s", "xu_warp_instructions_per_sm_cycle",
        "specified_max_clock_mhz", "power_limit_w")}
        for key, device in inputs["devices"].items()}
    device_demands, clocks = {}, {}
    if args.l4_ladder is not None:
        l4_ladder = load_ladder(args.l4_ladder)
        if args.ladder is None or l4_ladder["class_assignment"] != ladder["class_assignment"]:
            raise ValueError("the L4 ladder must use the same D5 class weights as --ladder")
        l4_demands = ladder_demands(l4_ladder)
        for key, device in inputs["devices"].items():
            wanted = device.get("demand_ladder_device")
            if wanted:
                if wanted not in l4_ladder["device"]:
                    raise ValueError(f"{key} wants a {wanted!r} ladder; --l4-ladder profiled {l4_ladder['device']!r}")
                device_demands[key] = l4_demands
        calibrated = [d for d in inputs["devices"].values()
                      if d.get("l1tex_sectors_per_sm_cycle_source") == "l4-ladder"]
        if len(calibrated) != 1 or calibrated[0]["label"] not in l4_ladder["device"]:
            raise ValueError("the L4 ladder must calibrate exactly the device it profiled")
        model["l4_l1tex_calibration"] = ladder_l1tex_calibration(l4_ladder)
        calibrated[0]["l1tex_sectors_per_sm_cycle"] = model["l4_l1tex_calibration"]["sectors_per_sm_cycle"]
        model["l4_ladder"] = ladder_extent(l4_ladder)
        sources.append(args.l4_ladder)
    if args.l4_clock_run is not None:
        report = json.loads(args.l4_clock_run.read_text())
        env = json.loads((args.l4_clock_run.parent / "env.json").read_text())
        product = re.search(r"Product Name\s*:\s*(.*)", env.get("nvidia_smi") or "")
        if report["screen"]["mode"] != "shape" or not product or product.group(1).strip() != "NVIDIA L4":
            raise ValueError("--l4-clock-run must be an L4 shape run beside its env.json")
        clock = statistics.median(float(row["telemetry"]["achieved_clock_mhz"]["median"])
                                  for row in measured_repeats(report))
        clocks["l4"] = (clock, f"{report['corpus']['name']} shape run, q={report['query_preparation']['n_queries']}")
        sources.append(args.l4_clock_run)
    if demands is not None and args.titan_run is not None:
        model["device_model"] = device_model(
            demands, inputs, json.loads(args.run.read_text()),
            json.loads(args.titan_run.read_text()), device_demands, clocks)
        sources.append(args.titan_run)
    atomic_write(args.output / "roofline-work.json", json.dumps(model, indent=2) + "\n")
    atomic_write(args.output / "roofline-constants.tex", constants_tex(model))
    atomic_write(args.output / "tables" / "roofline-work.tex", table_tex())
    outputs = ["roofline-work.json", "roofline-constants.tex", "tables/roofline-work.tex"]
    if "device_model" in model:
        atomic_write(args.output / "tables" / "roofline-device-caps.tex", device_caps_table(model["device_model"]))
        atomic_write(args.output / "tables" / "roofline-observed.tex", observed_table(model["device_model"]))
        atomic_write(args.output / "tables" / "scale-roofline.tex", scale_roofline_table(model["device_model"]))
        outputs.extend(["tables/roofline-device-caps.tex", "tables/roofline-observed.tex",
                        "tables/scale-roofline.tex"])
    manifest = {"generator": "scripts/analyze_roofline.py",
                "sources": [{"path": str(path), "sha256": sha256(path)} for path in sources],
                "outputs": outputs}
    atomic_write(args.output / "roofline-manifest.json", json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
