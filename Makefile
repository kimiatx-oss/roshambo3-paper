SHELL := /bin/bash

PYTHON ?= python3
PDFLATEX ?= pdflatex
BIBTEX ?= bibtex

PAPER := paper/main.tex
BUILD_DIR := build
GENERATED_DIR := generated
ASSET_STAMP := $(GENERATED_DIR)/.stamp
ANALYSIS_SCRIPT := scripts/generate_paper_assets.py
ROOFLINE_SCRIPT := scripts/analyze_roofline.py
EXPERIMENT_CONTEXT := data/experimental-context.json
TICKET_MILESTONES := data/ticket-milestones.json data/ticket-callouts.json
DEVELOPMENT_DATA := data/pitfall-classes.json data/development-incidents.json
ROOFLINE_INPUTS := data/roofline-work-model.json
ROOFLINE_RUN := runs/public-3bb39f69/blackwell/d5/panel4-shape.json
ROOFLINE_LADDER := runs/roofline-ladder-3bb39f69/ladder-summary.json
# sm_89 compiles the field atom loop as sm_70 does; the GV100 projection uses its demand.
ROOFLINE_L4_LADDER := runs/roofline-ladder-l4-3bb39f69/ladder-summary.json
# The L4 has no PubChem3D run; its observed clock comes from its LIT-PCBA shape run.
ROOFLINE_L4_CLOCK_RUN := runs/portability/l4/panel8-shape.json
ROOFLINE_TITAN_RUN := runs/public-3bb39f69/titanv/d5/panel4-shape.json

PUBLIC_RUN_INPUTS := $(shell find runs/public-3bb39f69 runs/rtx-pro-6000-3cr-3bb39f69 \
	runs/field-accuracy-3bb39f69 runs/litpcba-corpus-3bb39f69 \
	runs/archive/dudez-roshambo2-parity-t91 \
	runs/archive/volta-production-headtohead-t114 \
	-type f -name '*.json' 2>/dev/null | sort)
PROVENANCE_INPUTS := runs/ARCHIVE_INDEX.md \
	runs/archive/agent-development-record/record.json \
	runs/archive/agent-development-record/tickets.csv \
	runs/archive/agent-development-record/commit-days.csv
# The staged T169 optimizer-sensitivity package. Its ranking inputs are packed
# as .npz.xz in a release export and plain .npz once materialized; use either.
OPTSENS_DIR := revisions/optimizer-sensitivity
OPTSENS_INPUTS := $(firstword $(wildcard $(OPTSENS_DIR)/data/ranking-inputs.npz \
	$(OPTSENS_DIR)/data/ranking-inputs.npz.xz))
OPTSENS_WORK := $(GENERATED_DIR)/optimizer-sensitivity
OPTSENS_CONSTANTS := $(GENERATED_DIR)/constants-optimizer-sensitivity.tex
# Cross-backend portability table and CPU thread scaling (camera-ready). Rows
# without runs render as "pending"; PORTABILITY_FLAGS=--require-all refuses that.
# Each rule also writes its prose constants (portability-, cpu-scaling-constants.tex).
PORTABILITY_SPEC := data/portability-devices.json
PORTABILITY_PANEL := data/queries/PANEL-8.sdf
PORTABILITY_RUNS := $(shell find runs/portability runs/portability-scaling -type f \
	\( -name '*.json' -o -name '*.csv' \) ! -name '*.telemetry.csv' 2>/dev/null | sort)
PORTABILITY_TABLE := $(GENERATED_DIR)/tables/portability.tex
SCALING_TABLE := $(GENERATED_DIR)/tables/cpu-scaling.tex
PORTABILITY_FLAGS ?=
LATEX_SOURCES := $(shell find paper -type f \( -name '*.tex' -o -name '*.bib' \
	-o -name '*.sty' \) 2>/dev/null | sort)

.PHONY: all assets paper arxiv check test clean help
.DELETE_ON_ERROR:

all: paper

assets: $(ASSET_STAMP) $(OPTSENS_CONSTANTS) $(PORTABILITY_TABLE) $(SCALING_TABLE)

$(ASSET_STAMP): $(ANALYSIS_SCRIPT) $(ROOFLINE_SCRIPT) $(EXPERIMENT_CONTEXT) $(TICKET_MILESTONES) $(DEVELOPMENT_DATA) $(ROOFLINE_INPUTS) $(ROOFLINE_RUN) $(ROOFLINE_LADDER) $(ROOFLINE_L4_LADDER) $(ROOFLINE_L4_CLOCK_RUN) $(ROOFLINE_TITAN_RUN) $(PUBLIC_RUN_INPUTS) $(PROVENANCE_INPUTS)
	$(PYTHON) $(ANALYSIS_SCRIPT) --runs runs --output $(GENERATED_DIR)
	$(PYTHON) $(ROOFLINE_SCRIPT) --run $(ROOFLINE_RUN) --inputs $(ROOFLINE_INPUTS) --ladder $(ROOFLINE_LADDER) --l4-ladder $(ROOFLINE_L4_LADDER) --l4-clock-run $(ROOFLINE_L4_CLOCK_RUN) --titan-run $(ROOFLINE_TITAN_RUN) --output $(GENERATED_DIR)

$(OPTSENS_CONSTANTS): $(OPTSENS_INPUTS) $(OPTSENS_DIR)/data/isostep-fixture.meta.json \
		$(OPTSENS_DIR)/scripts/ranking_discordance.py $(OPTSENS_DIR)/scripts/emit_constants.py
	mkdir -p $(OPTSENS_WORK)
	case "$<" in \
	  *.xz) xz -dc "$<" > $(OPTSENS_WORK)/ranking-inputs.npz ;; \
	  *) cp "$<" $(OPTSENS_WORK)/ranking-inputs.npz ;; \
	esac
	$(PYTHON) $(OPTSENS_DIR)/scripts/ranking_discordance.py \
		--inputs $(OPTSENS_WORK)/ranking-inputs.npz --out $(OPTSENS_WORK)/ranking-discordance.json
	$(PYTHON) $(OPTSENS_DIR)/scripts/emit_constants.py \
		--discordance $(OPTSENS_WORK)/ranking-discordance.json \
		--fixture-meta $(OPTSENS_DIR)/data/isostep-fixture.meta.json --out $@

$(PORTABILITY_TABLE): scripts/analyze_portability.py $(PORTABILITY_SPEC) $(PORTABILITY_PANEL) $(PORTABILITY_RUNS)
	$(PYTHON) scripts/analyze_portability.py --runs runs/portability --devices $(PORTABILITY_SPEC) \
		--panel $(PORTABILITY_PANEL) --output $(GENERATED_DIR) $(PORTABILITY_FLAGS)

$(SCALING_TABLE): scripts/analyze_cpu_scaling.py $(PORTABILITY_SPEC) $(PORTABILITY_RUNS)
	$(PYTHON) scripts/analyze_cpu_scaling.py --runs runs/portability-scaling \
		--devices $(PORTABILITY_SPEC) --output $(GENERATED_DIR)

paper: $(BUILD_DIR)/main.pdf

$(BUILD_DIR)/main.pdf: $(LATEX_SOURCES) $(ASSET_STAMP) $(OPTSENS_CONSTANTS) $(PORTABILITY_TABLE) $(SCALING_TABLE)
	mkdir -p $(BUILD_DIR)
	TEXINPUTS=paper:generated: BIBINPUTS=paper: $(PDFLATEX) \
		-interaction=nonstopmode -halt-on-error -output-directory=$(BUILD_DIR) $(PAPER)
	BIBINPUTS=paper: $(BIBTEX) $(BUILD_DIR)/main
	TEXINPUTS=paper:generated: BIBINPUTS=paper: $(PDFLATEX) \
		-interaction=nonstopmode -halt-on-error -output-directory=$(BUILD_DIR) $(PAPER)
	TEXINPUTS=paper:generated: BIBINPUTS=paper: $(PDFLATEX) \
		-interaction=nonstopmode -halt-on-error -output-directory=$(BUILD_DIR) $(PAPER)

# arXiv source package (build/arxiv/, build/arxiv.tar.gz). ARXIV_CHECK=<pdf> also
# compiles it with pdflatex alone and requires that PDF's pages and text.
ARXIV_CHECK ?=
arxiv: $(BUILD_DIR)/main.pdf scripts/make_arxiv.py
	$(PYTHON) scripts/make_arxiv.py --build $(BUILD_DIR) --output $(BUILD_DIR)/arxiv \
		$(if $(ARXIV_CHECK),--check-pdf $(ARXIV_CHECK))

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

check: test paper

clean:
	rm -rf -- $(BUILD_DIR) $(GENERATED_DIR)

help:
	@echo 'make assets   regenerate LaTeX constants, tables, and figures'
	@echo 'make paper    regenerate assets and build build/main.pdf'
	@echo 'make check    run tests and build the paper'
	@echo 'make arxiv    package the built paper as arXiv LaTeX source'
	@echo 'make clean    remove only reproducible build products'
