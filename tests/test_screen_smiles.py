"""CPU-only checks for the paper workspace's one-off screening runner.

Building the paper needs neither the engine nor RDKit. The checks that drive
them skip unless both are installed (`pip install ..` and `rdkit`).
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np


SCRIPT = Path(__file__).parents[1] / "scripts" / "screen_smiles.py"
SPEC = importlib.util.spec_from_file_location("screen_smiles", SCRIPT)
screen_smiles = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(screen_smiles)

HAVE_ENGINE = importlib.util.find_spec("roshambo3") is not None
HAVE_RDKIT = importlib.util.find_spec("rdkit") is not None
needs_engine = unittest.skipUnless(HAVE_ENGINE, "needs the roshambo3 engine (pip install ..)")
needs_rdkit = unittest.skipUnless(HAVE_RDKIT, "needs RDKit")


class ScreenSmilesTests(unittest.TestCase):
    def test_read_smiles_preserves_nonblank_line_numbers(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "queries.smi"
            path.write_text("CCO\n\n c1ccccc1 \n", encoding="utf-8")
            self.assertEqual(screen_smiles.read_smiles(path),
                             [(1, "CCO"), (3, "c1ccccc1")])

    @needs_engine
    def test_shape_arm_is_shape_only(self):
        config, rank = screen_smiles.screen_config("shape", 0.5)
        self.assertFalse(config.color)
        self.assertEqual(config.mixing, 0.0)
        self.assertEqual(rank, "tanimoto_shape")

    def test_color_query_layout_matches_corpus_schema(self):
        self.assertFalse(screen_smiles.needs_color_query("shape", False))
        self.assertFalse(screen_smiles.needs_color_query("shape", True))
        self.assertTrue(screen_smiles.needs_color_query("rescore", False))

    @needs_engine
    @needs_rdkit
    def test_open_corpus_exposes_a_root_not_a_path(self):
        import roshambo3 as r3

        from rdkit import Chem
        from rdkit.Chem import AllChem
        with tempfile.TemporaryDirectory() as temp:
            molecule = Chem.AddHs(Chem.MolFromSmiles("CCO"))
            AllChem.EmbedMolecule(molecule, randomSeed=42)
            root = str(Path(temp) / "corpus")
            from roshambo3.prep import prepare
            prepare([molecule], root, workers=1)
            corpus = r3.open_corpus(root)
            self.assertEqual(corpus.root, root)

    @needs_engine
    def test_color_arms_use_their_distinct_placements(self):
        from roshambo3.backend.cuda import ColorPlacement

        rescore, rescore_rank = screen_smiles.screen_config("rescore", 0.5)
        combo, combo_rank = screen_smiles.screen_config("combo", 0.5)
        self.assertTrue(rescore.color)
        self.assertEqual(rescore.color_placement, ColorPlacement.AT_POSE)
        self.assertEqual(combo.color_placement, ColorPlacement.IN_GRADIENT)
        self.assertEqual(rescore_rank, "tanimoto_combination")
        self.assertEqual(combo_rank, "tanimoto_combination")

    @needs_rdkit
    def test_query_generation_is_seed_deterministic(self):
        first, _ = screen_smiles.build_query_molecules([(1, "CCO")])
        second, _ = screen_smiles.build_query_molecules([(1, "CCO")])
        first_xyz = first[0].GetConformer().GetPositions()
        second_xyz = second[0].GetConformer().GetPositions()
        np.testing.assert_allclose(first_xyz, second_xyz, rtol=0, atol=0)

    @needs_rdkit
    def test_query_generation_expands_multiple_conformers(self):
        molecules, metadata = screen_smiles.build_query_molecules(
            [(1, "CCO")], n_conformers=2)
        self.assertEqual(len(molecules), 2)
        self.assertEqual([m["name"] for m in metadata],
                         ["line_1_conf_001", "line_1_conf_002"])
        self.assertTrue(all(mol.GetNumConformers() == 1 for mol in molecules))

    @needs_engine
    @needs_rdkit
    def test_shape_query_uses_the_shape_interaction_matrix(self):
        import roshambo3 as r3

        molecules, _ = screen_smiles.build_query_molecules([(1, "CCO")])
        query = r3.load_queries(molecules)
        self.assertEqual(query.interaction_r.shape, (1, 1))

    def test_stability_reports_zero_variation_for_one_value(self):
        self.assertEqual(screen_smiles.stability([2.0]), {
            "min_s": 2.0, "median_s": 2.0, "max_s": 2.0,
            "pstdev_s": 0.0, "relative_spread": 0.0,
        })

    def test_fd_limit_report_has_soft_and_hard_values(self):
        limits = screen_smiles.configure_fd_limit()
        self.assertGreaterEqual(limits["soft"], 1)
        self.assertGreaterEqual(limits["hard"], limits["soft"])

    def test_launch_conformers_must_be_positive(self):
        with self.assertRaises(SystemExit):
            screen_smiles.parse_args([
                "--smiles-file", "queries.smi", "--corpus", "corpus",
                "--mode", "shape", "-k", "1", "--output-prefix", "out",
                "--launch-conformers", "0",
            ])

    def test_query_inputs_are_mutually_exclusive(self):
        common = ["--corpus", "corpus", "--mode", "shape", "-k", "1",
                  "--output-prefix", "out"]
        with self.assertRaises(SystemExit):
            screen_smiles.parse_args(common)
        with self.assertRaises(SystemExit):
            screen_smiles.parse_args([
                "--smiles-file", "q.smi", "--query-sdf", "q.sdf", *common])

    def test_force_and_skip_existing_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            screen_smiles.parse_args([
                "--smiles-file", "q.smi", "--corpus", "corpus",
                "--mode", "shape", "-k", "1", "--output-prefix", "out",
                "--force", "--skip-existing"])

    @needs_rdkit
    def test_exact_sdf_panel_retains_coordinates_and_limit(self):
        from rdkit import Chem
        from rdkit.Chem import AllChem

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "panel.sdf"
            writer = Chem.SDWriter(str(path))
            for name in ("first", "second"):
                mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))
                self.assertEqual(AllChem.EmbedMolecule(mol, randomSeed=7), 0)
                mol.SetProp("_Name", name)
                writer.write(mol)
            writer.close()
            molecules, metadata = screen_smiles.read_query_sdf(path, limit=1)
            self.assertEqual(len(molecules), 1)
            self.assertEqual(metadata[0]["name"], "first")
            self.assertEqual(metadata[0]["coordinate_source"], "input_sdf")

    def test_cache_drop_is_verified_on_a_small_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data.bin"
            path.write_bytes(b"x" * 8192)
            report = screen_smiles.drop_corpus_cache(temp)
            self.assertEqual(report["n_files"], 1)
            self.assertEqual(report["bytes"], 8192)
            self.assertIn("resident_fraction_after_drop", report)

    def test_readable_explicit_blackwell_build_configuration(self):
        build = SimpleNamespace(
            build_type="Release", with_cuda=True,
            cuda_architectures_requested="120-real", arch_list=["sm_120"],
            ptx_present=False, nvcc_version="13.2.78", nthreads=256)
        description = screen_smiles.describe_build_configuration(build)
        self.assertEqual(description["label"], "blackwell-sm120-explicit")
        self.assertIn("explicit Blackwell-only", description["summary"])
        self.assertIn("requested 120-real", description["summary"])
        self.assertIn("no PTX fallback", description["summary"])

    def test_readable_fatbin_build_configuration(self):
        build = SimpleNamespace(
            build_type="Release", with_cuda=True,
            cuda_architectures_requested=(
                "75-real,80-real,86-real,89-real,90-real,120-real,120-virtual"),
            arch_list=["sm_120", "sm_75", "sm_80", "sm_86", "sm_89", "sm_90"],
            ptx_present=True, nvcc_version="13.2.78", nthreads=256)
        description = screen_smiles.describe_build_configuration(build)
        self.assertEqual(description["label"], "portable-fatbin")
        self.assertIn("portable CUDA fat binary", description["summary"])
        self.assertIn("sm_120", description["summary"])
        self.assertIn("forward-compatible PTX included", description["summary"])

    def test_backend_defaults_cuda_workers_and_leaves_host_backends_to_their_policy(self):
        common = ["--query-sdf", "q.sdf", "--corpus", "corpus", "--mode", "shape",
                  "-k", "1", "--output-prefix", "out"]
        cuda = screen_smiles.parse_args(common)
        self.assertEqual((cuda.backend, cuda.workers),
                         ("cuda", screen_smiles.CUDA_DEFAULT_WORKERS))
        cpu = screen_smiles.parse_args([*common, "--backend", "cpu"])
        self.assertIsNone(cpu.workers)
        metal = screen_smiles.parse_args([*common, "--backend", "metal", "--workers", "6"])
        self.assertEqual(metal.workers, 6)
        self.assertEqual(screen_smiles.resolved_workers(metal), 6)
        with self.assertRaises(SystemExit):
            screen_smiles.parse_args([*common, "--backend", "rocm"])

    def test_host_backends_are_labeled_by_backend_not_as_missing_cuda(self):
        build = SimpleNamespace(
            build_type="Release", with_cuda=False, cuda_architectures_requested="",
            arch_list=[], ptx_present=False, nvcc_version="", nthreads=256)
        self.assertEqual(
            screen_smiles.describe_build_configuration(build, "metal")["label"], "metal")
        self.assertEqual(
            screen_smiles.describe_build_configuration(build)["label"], "cpu-only")

    def test_hits_csv_names_each_hit_by_molecule(self):
        class Catalog:
            def mol_ids(self, gids):
                return [int(g) // 10 for g in gids]

        hits = SimpleNamespace(
            query_name="q0", gids=[31, 12], scores=[0.9, 0.8],
            tanimoto_shape=[0.9, 0.8], tanimoto_color=[0.0, 0.0],
            tanimoto_combination=[0.9, 0.8])

        class Result(list):
            catalog = Catalog()

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hits.csv"
            screen_smiles.write_hits_csv(
                Result([hits]), {"q0": {"line": 1, "query_conformer": 0}}, path)
            rows = path.read_text().splitlines()
        self.assertTrue(rows[0].startswith("query,input_line,query_conformer,rank,gid,mol_id,"))
        self.assertEqual([row.split(",")[5] for row in rows[1:]], ["3", "1"])


if __name__ == "__main__":
    unittest.main()
