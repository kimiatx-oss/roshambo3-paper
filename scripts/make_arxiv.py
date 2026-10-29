#!/usr/bin/env python3
"""Package the built paper as an arXiv LaTeX source tarball.

    python scripts/make_arxiv.py --build build --output build/arxiv
    python scripts/make_arxiv.py --build build --output build/arxiv --check-pdf build/main.pdf

Run after `make paper`: the package takes the paper sources, the generated
constants, tables and figures the paper reads, and the BibTeX output
(`main.bbl`, which arXiv uses in place of `references.bib`). It writes them to
one flat directory, with `\\input` and `\\includegraphics` paths rewritten,
LaTeX comments removed from every .tex file, and a final `\\typeout` that makes
arXiv's autotex run pdflatex enough times to settle cross-references. The
style file is copied unchanged. The directory is also packed as
`<output>.tar.gz`.

`--check-pdf` compiles the package in a scratch directory with pdflatex alone,
as arXiv does, and requires the result to have the reference PDF's page count
and text.
"""

from __future__ import annotations

import argparse
import gzip
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = "main.tex"
INPUT = re.compile(r"\\input\{([^}]+)\}")
GRAPHICS = re.compile(r"(\\includegraphics(?:\[[^\]]*\])?)\{([^}]+)\}")
GRAPHICSPATH = re.compile(r"^\\graphicspath\{.*\}\s*$")
# arXiv reruns pdflatex while the log asks for a rerun; this line always asks.
RERUN = "\\typeout{get arXiv to do 4 passes: Label(s) may have changed. Rerun}\n"


def comment_start(line: str) -> int | None:
    """Index of the % that starts a comment, or None (a % after an odd run of
    backslashes is a literal percent sign)."""
    for match in re.finditer("%", line):
        backslashes = len(line[:match.start()]) - len(line[:match.start()].rstrip("\\"))
        if backslashes % 2 == 0:
            return match.start()
    return None


def strip_comments(text: str) -> str:
    """Remove LaTeX comments. A line that is only a comment is dropped; a
    comment after text keeps its %, which still swallows the line end."""
    out = []
    for line in text.splitlines(keepends=True):
        start = comment_start(line)
        if start is None:
            out.append(line)
        elif line[:start].strip():
            out.append(line[:start + 1] + "\n")
    return "".join(out)


def flat_name(path: str) -> str:
    name = Path(path).name
    return name if name.endswith(".tex") else name + ".tex"


def collect(paper: Path, generated: Path) -> tuple[dict[str, str], dict[str, Path]]:
    """Walk the \\input tree from main.tex. Returns the rewritten .tex files by
    flat name and the figure files they include by flat name."""
    tex: dict[str, str] = {}
    figures: dict[str, Path] = {}
    sources: dict[str, Path] = {}
    pending = [paper / MAIN]
    while pending:
        source = pending.pop()
        name = flat_name(source.name)
        if name in sources:
            if sources[name] != source:
                raise SystemExit(f"two inputs flatten to {name}: {sources[name]}, {source}")
            continue
        sources[name] = source
        text = strip_comments(source.read_text(encoding="utf-8"))

        def repoint_input(match: re.Match) -> str:
            target = match.group(1)
            if not target.endswith(".tex"):
                target += ".tex"
            for base in (paper, generated.parent):
                if (base / target).is_file():
                    pending.append(base / target)
                    break
            else:
                raise SystemExit(f"{source}: cannot find \\input{{{match.group(1)}}}")
            return "\\input{" + flat_name(target) + "}"

        def repoint_graphics(match: re.Match) -> str:
            target = match.group(2)
            found = next((p for p in (paper / target, generated / "figures" / target)
                          if p.is_file()), None)
            if found is None:
                raise SystemExit(f"{source}: cannot find figure {target}")
            if figures.setdefault(found.name, found) != found:
                raise SystemExit(f"two figures flatten to {found.name}")
            return match.group(1) + "{" + found.name + "}"

        text = INPUT.sub(repoint_input, text)
        text = GRAPHICS.sub(repoint_graphics, text)
        text = "".join(line for line in text.splitlines(keepends=True)
                       if not GRAPHICSPATH.match(line))
        tex[name] = text
    if set(tex) & set(figures):
        raise SystemExit("a figure and a .tex input share a name")
    tex[MAIN] = tex[MAIN].rstrip("\n") + "\n" + RERUN
    return tex, figures


def write_package(paper: Path, generated: Path, build: Path, output: Path) -> list[str]:
    tex, figures = collect(paper, generated)
    bbl = build / "main.bbl"
    if not bbl.is_file():
        raise SystemExit(f"{bbl} is missing; run `make paper` first")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, text in tex.items():
        (output / name).write_text(text, encoding="utf-8")
    for name, source in figures.items():
        shutil.copyfile(source, output / name)
    for style in sorted(paper.glob("*.sty")):
        shutil.copyfile(style, output / style.name)
    shutil.copyfile(bbl, output / "main.bbl")
    names = sorted(p.name for p in output.iterdir())
    tarball = output.parent / (output.name + ".tar.gz")
    with open(tarball, "wb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as packed, \
            tarfile.open(fileobj=packed, mode="w") as tar:
        for name in names:
            # Fixed metadata: the tarball depends only on the file contents.
            info = tar.gettarinfo(output / name, arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with open(output / name, "rb") as handle:
                tar.addfile(info, handle)
    return names


def pdf_text(pdf: Path) -> str:
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True,
                          capture_output=True, text=True).stdout
    return "\n".join(line.rstrip() for line in text.splitlines())


def page_count(pdf: Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True,
                          text=True).stdout
    return int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))


def check_pdf(package: Path, reference: Path, pdflatex: str) -> None:
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch) / "arxiv"
        shutil.copytree(package, work)
        env = {k: v for k, v in os.environ.items() if k not in ("TEXINPUTS", "BIBINPUTS")}
        for _ in range(4):
            subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", MAIN],
                           cwd=work, env=env, check=True, stdout=subprocess.DEVNULL)
        built = work / "main.pdf"
        problems = []
        if page_count(built) != page_count(reference):
            problems.append(f"{page_count(built)} pages, reference has {page_count(reference)}")
        if pdf_text(built) != pdf_text(reference):
            problems.append("text differs from the reference PDF")
        log = (work / "main.log").read_text(encoding="latin-1")
        for warning in ("undefined references", "Citation", "Rerun to get"):
            if re.search(rf"LaTeX Warning:.*{warning}", log):
                problems.append(f"log warns: {warning}")
        if problems:
            raise SystemExit("arXiv package check failed: " + "; ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paper", type=Path, default=ROOT / "paper")
    parser.add_argument("--generated", type=Path, default=ROOT / "generated")
    parser.add_argument("--build", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "arxiv")
    parser.add_argument("--check-pdf", type=Path,
                        help="reference PDF the package must reproduce (pages and text)")
    parser.add_argument("--pdflatex", default=os.environ.get("PDFLATEX", "pdflatex"))
    args = parser.parse_args()
    names = write_package(args.paper, args.generated, args.build, args.output)
    print(f"{args.output}: {len(names)} files")
    if args.check_pdf:
        check_pdf(args.output, args.check_pdf, args.pdflatex)
        print(f"compiles with pdflatex alone; pages and text match {args.check_pdf}")


if __name__ == "__main__":
    sys.exit(main())
