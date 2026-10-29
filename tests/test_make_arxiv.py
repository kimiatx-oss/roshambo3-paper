"""Tests for the arXiv source packager."""

from __future__ import annotations

import importlib.util
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("make_arxiv", ROOT / "scripts" / "make_arxiv.py")
make_arxiv = importlib.util.module_from_spec(SPEC)
sys.modules["make_arxiv"] = make_arxiv
SPEC.loader.exec_module(make_arxiv)


class StripCommentsTest(unittest.TestCase):
    def test_comment_only_lines_are_dropped(self):
        self.assertEqual(make_arxiv.strip_comments("a\n% note\n  % indented\nb\n"), "a\nb\n")

    def test_trailing_comment_keeps_its_percent(self):
        self.assertEqual(make_arxiv.strip_comments("text% why\n"), "text%\n")

    def test_escaped_percent_is_text(self):
        self.assertEqual(make_arxiv.strip_comments("50\\% of it\n"), "50\\% of it\n")
        self.assertEqual(make_arxiv.strip_comments("50\\% % note\n"), "50\\% %\n")

    def test_percent_after_line_break_is_a_comment(self):
        self.assertEqual(make_arxiv.strip_comments("a & b \\\\% row note\n"), "a & b \\\\%\n")


class PackageTest(unittest.TestCase):
    def make_tree(self, root: Path) -> tuple[Path, Path, Path]:
        paper, generated, build = root / "paper", root / "generated", root / "build"
        (generated / "tables").mkdir(parents=True)
        (generated / "figures").mkdir()
        paper.mkdir()
        build.mkdir()
        (paper / "main.tex").write_text(
            "% Internal note.\n"
            "\\input{generated/constants.tex}\n"
            "\\graphicspath{{generated/figures/}}\n"
            "\\begin{document}\n"
            "\\input{generated/tables/results.tex}\n"
            "\\includegraphics[width=1in]{plot.pdf}\n"
            "\\input{supplement.tex}\n"
            "\\end{document}\n")
        (paper / "supplement.tex").write_text("Supplement.% trailing\n")
        (paper / "style.sty").write_text("% The style keeps its comments.\n")
        (paper / "references.bib").write_text("@misc{x}\n")
        (generated / "constants.tex").write_text("% Generated; do not edit.\n\\newcommand{\\X}{1}\n")
        (generated / "tables" / "results.tex").write_text("\\X\\%\n")
        (generated / "figures" / "plot.pdf").write_bytes(b"%PDF-1.5\n")
        (generated / "figures" / "plot.svg").write_text("<svg/>")
        (build / "main.bbl").write_text("\\begin{thebibliography}{1}\\end{thebibliography}\n")
        return paper, generated, build

    def test_package_is_flat_and_complete(self):
        with tempfile.TemporaryDirectory() as scratch:
            paper, generated, build = self.make_tree(Path(scratch))
            output = build / "arxiv"
            names = make_arxiv.write_package(paper, generated, build, output)
            self.assertEqual(names, ["constants.tex", "main.bbl", "main.tex", "plot.pdf",
                                     "results.tex", "style.sty", "supplement.tex"])
            main = (output / "main.tex").read_text()
            self.assertNotIn("Internal note", main)
            self.assertNotIn("graphicspath", main)
            self.assertIn("\\input{constants.tex}", main)
            self.assertIn("\\input{results.tex}", main)
            self.assertIn("\\includegraphics[width=1in]{plot.pdf}", main)
            self.assertTrue(main.endswith(make_arxiv.RERUN))
            self.assertEqual((output / "constants.tex").read_text(), "\\newcommand{\\X}{1}\n")
            self.assertEqual((output / "supplement.tex").read_text(), "Supplement.%\n")
            self.assertIn("comments", (output / "style.sty").read_text())
            with tarfile.open(build / "arxiv.tar.gz") as tar:
                self.assertEqual(sorted(tar.getnames()), names)
                self.assertTrue(all(m.mtime == 0 and m.uid == 0 for m in tar.getmembers()))
            first = (build / "arxiv.tar.gz").read_bytes()
            make_arxiv.write_package(paper, generated, build, output)
            self.assertEqual((build / "arxiv.tar.gz").read_bytes(), first)

    def test_missing_bbl_is_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            paper, generated, build = self.make_tree(Path(scratch))
            (build / "main.bbl").unlink()
            with self.assertRaises(SystemExit):
                make_arxiv.write_package(paper, generated, build, build / "arxiv")

    def test_colliding_inputs_are_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            paper, generated, build = self.make_tree(Path(scratch))
            (generated / "tables" / "constants.tex").write_text("\n")
            main = paper / "main.tex"
            main.write_text(main.read_text().replace(
                "\\begin{document}", "\\input{generated/tables/constants.tex}\n\\begin{document}"))
            with self.assertRaises(SystemExit):
                make_arxiv.write_package(paper, generated, build, build / "arxiv")


if __name__ == "__main__":
    unittest.main()
