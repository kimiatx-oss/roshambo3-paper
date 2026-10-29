# Linear-time Shape Alignment with ROSHAMBO3: paper repository

This repository accompanies the NeurIPS 2026 ML4Molecules workshop paper
"Linear-time Shape Alignment with ROSHAMBO3". The engine itself is at
<https://github.com/kimiatx-oss/roshambo3>.

It contains:

| Path | Contents |
|---|---|
| `paper/` | LaTeX sources of the paper and its supplement |
| `scripts/`, `data/` | Analysis scripts and inputs that generate every number, table and figure in the paper, plus the benchmark harnesses (`screen_smiles.py`, `portability_campaign.sh`, `profile_roofline.py`) and the LIT-PCBA rebuild recipe (`LITPCBA.md`) |
| `runs/` | The run records the build reads (see `runs/ARCHIVE_INDEX.md`) |
| `revisions/optimizer-sensitivity/` | The ROSHAMBO2-versus-ROSHAMBO3 ranking-overlap analysis and its inputs |
| `tests/` | Tests of the analysis scripts |
| `tickets/`, `decisions/` | An excerpt of the development record described in the paper's Appendix E (see below) |

## Building the paper

Every number, table and figure is regenerated from the records under `runs/`
and `data/`; `generated/` and `build/` are not tracked. The build needs no GPU
and does not use the screening engine.

Requirements:

* TeX Live with the NeurIPS template's packages. On Debian or Ubuntu:
  `texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended`
  (MacTeX or a full TeX Live also work).
* `mutool` (Debian/Ubuntu `mupdf-tools`, Homebrew `mupdf-tools`), which converts
  the generated SVG figures to PDF, and `xz`.
* Python 3.10 or later with the packages in `requirements.txt`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make check PYTHON=.venv/bin/python PORTABILITY_FLAGS=--require-all
```

`make check` runs the analysis tests and writes `build/main.pdf`; `make paper`
skips the tests. `PORTABILITY_FLAGS=--require-all` refuses to render a
portability row whose runs are missing (without it, such cells read "pending").
The tests of the screening harness (`tests/test_screen_smiles.py`) that drive
the engine or RDKit skip unless ROSHAMBO3 and RDKit are installed.

`make arxiv` packages the built paper as arXiv LaTeX source in `build/arxiv/`
and `build/arxiv.tar.gz`: one flat directory with comments removed and
`main.bbl` in place of the bibliography database. `ARXIV_CHECK=<pdf>` also
compiles the package with pdflatex alone and requires that PDF's page count
and text (`pdftotext`, `pdfinfo`: Debian/Ubuntu `poppler-utils`).

## Data

Run records are redacted: data locations read `$EXTERNAL_DATA`, and device
serial numbers and UUIDs are removed. Runs on the private 3CR library carry
counts, rates and hashes only. No corpus is distributed; `scripts/LITPCBA.md`
rebuilds the LIT-PCBA corpus from its public sources, and
`data/queries/PANEL-8.sdf` is the public query panel used for the portability
study. Commit hashes in the records refer to the internal development
repository, whose history is not published; the benchmarked screening kernels
are those of ROSHAMBO3 1.0.0.

## The development record (excerpt)

The paper's Appendix E describes how ROSHAMBO3 was built by AI coding agents
working from tickets, standing decisions and numbered pitfalls. The figures and
counts in the paper come from the full record through
`runs/archive/agent-development-record/`, a field-level export (ticket ids,
epochs, model tiers, dates and dependencies). The full record also contains
confidential chemistry and infrastructure detail, so this repository ships an
edited excerpt:

* `tickets/CONVENTIONS.md`: the working rules, the numbered pitfalls and the
  measurement protocols every ticket cites.
* Two blocks of tickets, chosen to show the two modes the paper describes:
  * T178–T224 (CPU combo): a long dependency chain, each ticket implemented by
    one model tier and reviewed by another and each building on the previous
    measurement.
  * T281–T298 and T303 (corpus format 3): one planning ticket decomposed into a
    dependency graph of tickets, approved in batches and worked in parallel by
    several models from two vendors.
  T208 and T299–T302, which concern internal corpora and release logistics, are
  omitted.
* `decisions/`: the standing decisions those tickets and the paper cite
  (`decisions/INDEX.md`).

The excerpt is edited for confidentiality: internal corpus names, paths, hosts
and quotations were removed or generalized. Tickets cite result directories
(`results/TNNN/`), scripts, other tickets and decisions that are not part of
this repository; those citations are left in place as identifiers.

## License

MIT; see `LICENSE`.
