# ROSHAMBO3 paper performance campaign (GPU, internal hosts).  Run with
#   make -C scripts campaign SOURCE_TREE=<roshambo3 checkout> CORPUS_...=<corpus dirs>
# Individual targets are resumable because the runner refuses to overwrite.

.NOTPARALLEL:
.DELETE_ON_ERROR:

PYTHON ?= ../.venv/bin/python
ROOFLINE_PYTHON ?= ../.venv-sm120/bin/python
RUNNER := screen_smiles.py
SOURCE_TREE ?= $(error set SOURCE_TREE to a roshambo3 checkout)
RUN_DIR ?= ../runs/campaign

# Corpus and panel locations; set on the command line.
CORPUS_3CR ?=
CORPUS_LITPCBA ?=
CORPUS_D5 ?=
LITPCBA_PANEL ?=
PRIVATE_QUERY ?= private-query.smi

K ?= 1000
WORKERS ?= 8
PREFETCH ?= 8
LAUNCH ?= 262144
MIXING ?= 0.5
EXTRA ?=

COMMON = --source-tree $(SOURCE_TREE) -k $(K) --workers $(WORKERS) \
	--prefetch $(PREFETCH) --launch-conformers $(LAUNCH) \
	--telemetry-interval 1 --lock-timeout 3600 --skip-existing $(EXTRA)
PRIVATE = --smiles-file $(PRIVATE_QUERY) --corpus $(CORPUS_3CR)
PUBLIC_PANEL = --query-sdf $(LITPCBA_PANEL)

.PHONY: litpcba-corpus portability portability-smoke validate-portability all campaign private public stability saturation modes cache profile-roofline \
	litpcba d5 followup litpcba-extended saturation-q16 \
	validate validate-common validate-private validate-public help

all: campaign

# The dependency graph documents the intended order.  .NOTPARALLEL is
# deliberate: even `make -j` may never dispatch benchmark arms concurrently.
campaign: private public
private: validate-private stability saturation modes cache
public: validate-public litpcba d5
followup: litpcba-extended saturation-q16

validate: validate-private validate-public

validate-common:
	@test -x "$(PYTHON)"
	@test -f "$(RUNNER)"
	@test -f "$(LITPCBA_PANEL)"

validate-private: validate-common
	@test -f "$(PRIVATE_QUERY)"
	@test -d "$(CORPUS_3CR)"
	@mkdir -p "$(RUN_DIR)/3cr"

validate-public: validate-common
	@test -d "$(CORPUS_LITPCBA)"
	@test -d "$(CORPUS_D5)"
	@mkdir -p "$(RUN_DIR)/litpcba" "$(RUN_DIR)/d5"

# Steady-state repeat stability at the under-filled and thermally saturated
# endpoints.  One unreported warmup is followed by five timed observations.
stability:
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 1 --warmups 1 --repeats 5 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/stability-combo-q1
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 4 --warmups 1 --repeats 5 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/stability-combo-q4

# q=1 and q=4 come from stability above; these two interior/extrapolation
# points complete the q={1,2,4,8} saturation curve without duplicate work.
saturation:
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 2 --warmups 1 --repeats 3 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/saturation-combo-q2
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 8 --warmups 1 --repeats 3 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/saturation-combo-q8

# One extrapolation point beyond the original q={1,2,4,8} curve.  This is
# intentionally a separate output so the completed campaign remains immutable.
saturation-q16: validate-private
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 16 --warmups 1 --repeats 3 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/saturation-combo-q16

# Three Latin-square rounds reduce order/thermal bias in the matched
# shape / shape+color-rescore / joint-combo comparison.  The primer is not
# part of the comparison; each measured arm is one independent observation.
modes:
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 4 --warmups 1 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-primer
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode shape   --query-conformers 4 --repeats 1 --cache-mode warm --output-prefix $(RUN_DIR)/3cr/modes-r1-shape
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode rescore --query-conformers 4 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-r1-rescore
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo   --query-conformers 4 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-r1-combo
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode rescore --query-conformers 4 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-r2-rescore
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo   --query-conformers 4 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-r2-combo
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode shape   --query-conformers 4 --repeats 1 --cache-mode warm --output-prefix $(RUN_DIR)/3cr/modes-r2-shape
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo   --query-conformers 4 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-r3-combo
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode shape   --query-conformers 4 --repeats 1 --cache-mode warm --output-prefix $(RUN_DIR)/3cr/modes-r3-shape
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode rescore --query-conformers 4 --repeats 1 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/modes-r3-rescore

# One explicitly cold q=4 run.  Compare with the warm q=4 stability record.
cache:
	$(PYTHON) $(RUNNER) $(COMMON) $(PRIVATE) --mode combo --query-conformers 4 --warmups 0 --repeats 1 --cache-mode cold --mixing $(MIXING) --output-prefix $(RUN_DIR)/3cr/cache-cold-combo-q4

# Fully redistributable query/library arm.  PANEL-8 gives enough aggregate
# work for stable timings even though LIT-PCBA is not a headline-scale corpus.
litpcba:
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) --mode shape --warmups 1 --repeats 5 --cache-mode warm --output-prefix $(RUN_DIR)/litpcba/panel8-shape
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) --mode rescore --warmups 1 --repeats 5 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/litpcba/panel8-rescore
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) --mode combo --warmups 1 --repeats 5 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/litpcba/panel8-combo

# Longer public timing series for the short LIT-PCBA arms.  Three warmups and
# eleven timed repeats match the benchmark harness's decision-grade convention.
litpcba-extended: validate-public
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) --mode shape --warmups 3 --repeats 11 --cache-mode warm --output-prefix $(RUN_DIR)/litpcba/panel8-shape-extended
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) --mode rescore --warmups 3 --repeats 11 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/litpcba/panel8-rescore-extended
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) --mode combo --warmups 3 --repeats 11 --cache-mode warm --mixing $(MIXING) --output-prefix $(RUN_DIR)/litpcba/panel8-combo-extended

# Public ultra-large headline: first four deposited LIT-PCBA query structures
# against the 512M-conformer PubChem3D-derived D5 corpus.  D5 is shape-only.
d5:
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --query-limit 4 --corpus $(CORPUS_D5) --mode shape --warmups 1 --repeats 3 --cache-mode warm --output-prefix $(RUN_DIR)/d5/panel4-shape
	$(PYTHON) $(RUNNER) $(COMMON) $(PUBLIC_PANEL) --query-limit 4 --corpus $(CORPUS_D5) --mode shape --warmups 0 --repeats 1 --cache-mode cold --output-prefix $(RUN_DIR)/d5/panel4-shape-cold

# Cross-backend portability table (camera-ready). One device per invocation,
# every device from the same frozen source commit; see PORTABILITY.md.
#   make portability-smoke BACKEND=cpu DEVICE_KEY=neoverse-v2
#   make portability       BACKEND=cpu DEVICE_KEY=neoverse-v2
# DEVICE_KEY must be a key in ../data/portability-devices.json. CUDA keeps the
# campaign's worker, prefetch and launch settings; CPU and Metal use their
# backend's own policies.
BACKEND ?= cuda
DEVICE_KEY ?=
PORT_RUN_DIR ?= ../runs/portability
PORT_SMOKE_DIR ?= ../runs/portability-smoke
PORT_WARMUPS ?= 1
PORT_REPEATS ?= $(if $(filter cpu,$(BACKEND)),3,5)
PORT_TUNING = $(if $(filter cuda,$(BACKEND)),--workers $(WORKERS) --prefetch $(PREFETCH) --launch-conformers $(LAUNCH),)
PORT_COMMON = --source-tree $(SOURCE_TREE) -k $(K) --backend $(BACKEND) $(PORT_TUNING) \
	--telemetry-interval 1 --lock-timeout 3600 $(PUBLIC_PANEL) --corpus $(CORPUS_LITPCBA) \
	--cache-mode warm --mixing $(MIXING) $(EXTRA)

validate-portability: validate-common
	@test -n "$(DEVICE_KEY)" || { echo "set DEVICE_KEY"; exit 1; }
	@grep -q '"key": "$(DEVICE_KEY)"' ../data/portability-devices.json || \
		{ echo "unknown DEVICE_KEY $(DEVICE_KEY)"; exit 1; }
	@grep -q '"key": "$(DEVICE_KEY)", "name": "[^"]*", "kind": "[a-z]*", "backend": "$(BACKEND)"' \
		../data/portability-devices.json || \
		{ echo "$(DEVICE_KEY) is not a $(BACKEND) device"; exit 1; }
	@test -d "$(CORPUS_LITPCBA)"
	@mkdir -p "$(PORT_RUN_DIR)/$(DEVICE_KEY)" "$(PORT_SMOKE_DIR)/$(DEVICE_KEY)"

# One query, one combo screen over the whole corpus with no warmup: proves the
# backend accepts every LIT-PCBA bucket before the timed campaign starts.
# Its output stays out of the table's directory.
portability-smoke: validate-portability
	$(PYTHON) $(RUNNER) $(PORT_COMMON) --query-limit 1 --mode combo --warmups 0 --repeats 1 \
		--force --output-prefix $(PORT_SMOKE_DIR)/$(DEVICE_KEY)/panel1-combo

portability: validate-portability
	$(PYTHON) $(RUNNER) $(PORT_COMMON) --skip-existing --mode shape --warmups $(PORT_WARMUPS) --repeats $(PORT_REPEATS) --output-prefix $(PORT_RUN_DIR)/$(DEVICE_KEY)/panel8-shape
	$(PYTHON) $(RUNNER) $(PORT_COMMON) --skip-existing --mode rescore --warmups $(PORT_WARMUPS) --repeats $(PORT_REPEATS) --output-prefix $(PORT_RUN_DIR)/$(DEVICE_KEY)/panel8-rescore
	$(PYTHON) $(RUNNER) $(PORT_COMMON) --skip-existing --mode combo --warmups $(PORT_WARMUPS) --repeats $(PORT_REPEATS) --output-prefix $(PORT_RUN_DIR)/$(DEVICE_KEY)/panel8-combo

# Rebuild the LIT-PCBA color corpus and PANEL-8 from the public release; see
# LITPCBA.md. GEN_PYTHON is a venv with litpcba-requirements.txt; PYTHON (the
# tool's venv) runs the final prepare. LITPCBA_LIMIT=300 makes a smoke build.
GEN_PYTHON ?= python3
LITPCBA_BUILD ?= ../build/litpcba
LITPCBA_LIMIT ?= 0
LITPCBA_GPUS ?= 0
litpcba-corpus:
	PATH=$(dir $(GEN_PYTHON)):$$PATH $(GEN_PYTHON) build_litpcba.py all --out $(LITPCBA_BUILD) \
		--limit $(LITPCBA_LIMIT) --gpu-ids $(LITPCBA_GPUS) --tool-python $(PYTHON)

help:
	@echo "campaign  full serial campaign (default)"
	@echo "private   3CR stability, saturation, modes, and cache arms"
	@echo "public    LIT-PCBA mode comparison plus D5 public headline"
	@echo "followup  extended LIT-PCBA repeats plus the 3CR q=16 point"
	@echo "litpcba-corpus  rebuild the LIT-PCBA corpus and PANEL-8 from source (LITPCBA.md)"
	@echo "litpcba-extended and saturation-q16 may also be run separately"
	@echo "Complete outputs are skipped on restart. Remove --skip-existing from COMMON"
	@echo "before using EXTRA=--force to deliberately replace outputs."
	@echo "profile-roofline runs the field and analytic ncu profile targets (wrap each in ncu)"

profile-roofline:
	# profile_roofline.py is the ncu target; the ncu wrapper script is not shipped.
	# Run each arm under ncu (see runs/roofline-ladder-l4-3bb39f69/README.md for flags).
	for arm in field analytic; do \
	  $(ROOFLINE_PYTHON) profile_roofline.py --arm $$arm --corpus $(CORPUS_D5) --panel $(LITPCBA_PANEL) || exit 1; \
	done
