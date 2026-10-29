"""Tests for the LIT-PCBA rebuild's archive parsing and compound index."""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("build_litpcba", ROOT / "scripts" / "build_litpcba.py")
build = importlib.util.module_from_spec(SPEC)
sys.modules["build_litpcba"] = build
SPEC.loader.exec_module(build)

try:
    import rdkit  # noqa: F401
    HAVE_RDKIT = True
except ImportError:
    HAVE_RDKIT = False


def archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


MEMBERS = {
    # A compound is an active of one target and an inactive of another: one row.
    "ALDH1/actives.smi": b"CCO 101\nc1ccccc1 102\n",
    "ALDH1/inactives.smi": b"CCN 103\n",
    "ESR1_ago/actives.smi": b"CCN 103\n",
    "ESR1_ago/inactives.smi": b"CCO 101\n\n",
    "ALDH1/4wp7_ligand.mol2": b"@<TRIPOS>MOLECULE\n",
    "ALDH1/README.txt": b"ignored\n",
}


class ArchiveTests(unittest.TestCase):
    def test_members_yield_smiles_rows_and_templates(self):
        with tempfile.TemporaryDirectory() as temp:
            tgz = Path(temp) / "full_data.tgz"
            archive(tgz, MEMBERS)
            rows = list(build._tar_members(tgz))
        smi = [r for r in rows if r[0] == "smi"]
        mol2 = [r for r in rows if r[0] == "mol2"]
        self.assertEqual(len(smi), 5)
        self.assertIn(("smi", "ESR1_ago", "inactive", "101", "CCO"), smi)
        self.assertEqual([(r[1], r[2]) for r in mol2], [("ALDH1", "4wp7")])

    def test_malformed_smiles_line_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            tgz = Path(temp) / "full_data.tgz"
            archive(tgz, {"ALDH1/actives.smi": b"CCO 101 extra\n"})
            with self.assertRaises(ValueError):
                list(build._tar_members(tgz))


@unittest.skipUnless(HAVE_RDKIT, "RDKit is required for the index step")
class IndexTests(unittest.TestCase):
    def run_index(self, members):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        out = Path(temp.name)
        (out / "raw").mkdir()
        archive(out / "raw" / "full_data.tgz", members)
        build.index(out, argparse.Namespace(workers=1))
        return out

    def test_compounds_are_unique_by_cid_and_labels_keep_every_row(self):
        out = self.run_index(MEMBERS)
        compounds = [json.loads(l) for l in (out / "index" / "compounds.jsonl").read_text().splitlines()]
        labels = (out / "index" / "labels.jsonl").read_text().splitlines()
        self.assertEqual(sorted(c["cid"] for c in compounds), ["101", "102", "103"])
        self.assertEqual({c["ext_id"] for c in compounds}, {"CID101", "CID102", "CID103"})
        self.assertEqual(len(labels), 5)
        summary = json.loads((out / "index" / "summary.json").read_text())
        self.assertEqual(summary["n_unique_compounds"], 3)
        # A second run resumes rather than rebuilding.
        (out / "index" / "compounds.jsonl").write_text("sentinel\n")
        build.index(out, argparse.Namespace(workers=1))
        self.assertEqual((out / "index" / "compounds.jsonl").read_text(), "sentinel\n")

    def test_a_cid_with_two_smiles_is_refused(self):
        with self.assertRaises(ValueError):
            self.run_index({"A/actives.smi": b"CCO 101\n", "B/actives.smi": b"CCN 101\n"})


if __name__ == "__main__":
    unittest.main()
