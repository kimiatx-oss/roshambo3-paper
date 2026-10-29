#!/bin/sh
# Run the camera-ready portability campaign on THIS machine.
#
#   portability_campaign.sh env       record the install and host once
#   portability_campaign.sh smoke     one query, one combo pass over the corpus
#   portability_campaign.sh table     PANEL-8 x {shape, rescore, combo}, timed
#   portability_campaign.sh scaling   CPU thread ladder (Linux, BACKEND=cpu)
#   portability_campaign.sh threads   unpinned worker-count ladder (any OS, BACKEND=cpu)
#
# Configuration comes from the environment, so the script names no host or path:
#
#   R3_PYTHON   python of the venv the tool is installed in
#   R3_SRC      the clean checkout the tool was installed from
#   R3_CORPUS   LIT-PCBA color corpus directory
#   R3_PANEL    PANEL-8.sdf
#   R3_OUT      output root; runs land in $R3_OUT/$DEVICE_KEY/...
#   DEVICE_KEY  row key, e.g. xeon-8581c
#   BACKEND     cuda | cpu | metal
#   R3_DEVICE   optional GPU index (cuda/metal); omitted means device 0
#   R3_THREADS  worker counts for `threads`, e.g. "4 8 10 12 14"
#   DRYRUN=1    print the screen_smiles.py commands instead of running them
#
# The screen flags are the scripts/Makefile `portability` targets' flags
# (PORT_COMMON plus the per-target ones). Calling the runner directly keeps
# outputs outside the checkout, so the source tree stays clean, and lets a
# device absent from data/portability-devices.json run unchanged. Every run
# writes a <prefix>.run.json sidecar: the CPU list it was confined to, the
# worker count, and this script's own sha256.
set -eu

die() { echo "portability_campaign: $*" >&2; exit 2; }
for v in R3_PYTHON R3_SRC R3_CORPUS R3_PANEL R3_OUT DEVICE_KEY BACKEND; do
    eval "test -n \"\${$v:-}\"" || die "set $v"
done
case "$BACKEND" in cuda|cpu|metal) ;; *) die "BACKEND must be cuda, cpu or metal" ;; esac
test -d "$R3_CORPUS" || die "no corpus at $R3_CORPUS"
test -f "$R3_PANEL" || die "no query panel at $R3_PANEL"

SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
RUNNER=$R3_SRC/publication/scripts/screen_smiles.py
DEST=$R3_OUT/$DEVICE_KEY
K=1000
MIXING=0.5
REPEATS=5
test "$BACKEND" = cpu && REPEATS=3
TUNING=""
test "$BACKEND" = cuda && TUNING="--workers 8 --prefetch 8 --launch-conformers 262144"
DEVICE_ARG=""
test -n "${R3_DEVICE:-}" && DEVICE_ARG="--device $R3_DEVICE"
COMMON="--source-tree $R3_SRC -k $K --backend $BACKEND $TUNING $DEVICE_ARG \
--telemetry-interval 1 --lock-timeout 3600 --query-sdf $R3_PANEL --corpus $R3_CORPUS \
--cache-mode warm --mixing $MIXING"

# run <cpu-list or ""> <workers or ""> <output prefix> <screen flags...>
run() {
    cpus=$1; workers=$2; prefix=$3; shift 3
    pin=""
    test -n "$cpus" && pin="taskset -c $cpus"
    extra=""
    test -n "$workers" && extra="--workers $workers"
    # shellcheck disable=SC2086  # word splitting of the flag strings is intended
    if [ "${DRYRUN:-0}" = 1 ]; then
        echo $pin "$R3_PYTHON" "$RUNNER" $COMMON "$@" $extra --output-prefix "$prefix"
        return 0
    fi
    mkdir -p "$(dirname "$prefix")"
    started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    # shellcheck disable=SC2086
    $pin "$R3_PYTHON" "$RUNNER" $COMMON "$@" $extra --output-prefix "$prefix"
    # shellcheck disable=SC2086
    $pin "$R3_PYTHON" - "$prefix" "$SELF" "$started" "$cpus" "$workers" "$*" <<'EOF'
import hashlib, json, os, sys, time
prefix, script, started, cpus, workers, flags = sys.argv[1:7]
affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
record = {
    "started_utc": started,
    "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "taskset_cpus": cpus or None,
    "affinity": affinity,
    "workers_requested": int(workers) if workers else None,
    "flags": flags,
    "driver_sha256": hashlib.sha256(open(script, "rb").read()).hexdigest(),
}
with open(prefix + ".run.json", "w") as handle:
    json.dump(record, handle, indent=2)
    handle.write("\n")
EOF
}

cmd_env() {
    mkdir -p "$DEST"
    "$R3_PYTHON" - "$DEST/env.json" "$R3_SRC" "$R3_PANEL" "$R3_CORPUS" "$SELF" "$BACKEND" <<'EOF'
import glob, hashlib, json, os, platform, subprocess, sys
out, src, panel, corpus, script, backend = sys.argv[1:7]

def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

import roshambo3
from roshambo3 import get_build_info


def corpus_record(root):
    """A format-3 corpus: corpus.json's hash, conformer-id hash and fingerprint."""
    descriptor = os.path.join(root, "corpus.json")
    if not os.path.isfile(descriptor):
        raise SystemExit(f"{root} has no corpus.json: not a format-3 corpus")
    opened = roshambo3.open_corpus(root)
    return {"descriptor_sha256": sha(descriptor),
            "ids_sha256": opened.descriptor.get("ids_sha256"),
            "fingerprint": opened.fingerprint,
            "conformers": int(opened.n_conformers), "molecules": int(opened.n_molecules)}
stamps = {"cuda": get_build_info().__dict__}
try:
    from roshambo3.backend import cpu
    stamps["cpu"] = cpu.build_stamp()
except Exception as exc:          # no CPU extension in this build
    stamps["cpu"] = {"error": repr(exc)}
if backend == "metal":
    from roshambo3.backend import metal
    stamps["metal"] = metal.build_stamp()
dist = glob.glob(os.path.join(os.path.dirname(roshambo3.__file__), "..",
                              "roshambo3-*.dist-info", "direct_url.json"))
topology = {}
for path in sorted(glob.glob("/sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list")):
    topology[path.split("/")[5]] = open(path).read().strip()
record = {
    "install": {
        "checkout_head": sh("git", "-C", src, "rev-parse", "HEAD").strip(),
        "checkout_status": sh("git", "-C", src, "status", "--porcelain"),
        "package_path": os.path.dirname(os.path.realpath(roshambo3.__file__)),
        "editable": not os.path.realpath(roshambo3.__file__).startswith(os.path.realpath(sys.prefix)),
        "direct_url": json.load(open(dist[0])) if dist else None,
        "pip_freeze": sh(sys.executable, "-m", "pip", "freeze").splitlines(),
        "python": sys.version,
    },
    "tool_stamps": stamps,
    "panel_sha256": sha(panel),
    "corpus": corpus_record(corpus),
    "driver_sha256": sha(script),
    "platform": platform.platform(),
    "thread_siblings": topology,
    "lscpu": sh("lscpu") if sys.platform != "darwin" else None,
    "nvidia_smi": sh("nvidia-smi", "-q") if backend == "cuda" else None,
    "system_profiler": (sh("system_profiler", "SPHardwareDataType", "SPDisplaysDataType", "-json")
                        if sys.platform == "darwin" else None),
}
with open(out, "w") as handle:
    json.dump(record, handle, indent=2, default=str)
    handle.write("\n")
print(f"wrote {out}: checkout {record['install']['checkout_head'][:10]}, "
      f"cuda stamp {stamps['cuda'].get('git_sha', '?')[:10]}, "
      f"cpu target {stamps['cpu'].get('selected_target', '-')}")
EOF
}

cmd_smoke() {
    run "" "" "$DEST/smoke/panel1-combo" --query-limit 1 --mode combo --warmups 0 --repeats 1 --force
}

cmd_table() {
    for mode in shape rescore combo; do
        run "" "" "$DEST/table/panel8-$mode" --skip-existing --mode "$mode" --warmups 1 --repeats "$REPEATS"
    done
}

# CPU lists for N physical cores x S threads each, from sysfs. Arms smaller
# than the machine skip core 0, which takes the guest's interrupt load.
cpu_list() {
    n=$1; s=$2
    for f in /sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list; do
        cat "$f"
    done | sort -u -t, -k1,1n | awk -F, -v n="$n" -v s="$s" '
        { core[NR] = $0 } END {
            start = (n < NR) ? 2 : 1
            if (start + n - 1 > NR) exit 1
            out = ""
            for (i = start; i < start + n; i++) {
                if (s > split(core[i], sib, ",")) exit 1
                for (j = 1; j <= s; j++) out = out (out == "" ? "" : ",") sib[j]
            }
            print out
        }'
}

cmd_scaling() {
    test "$BACKEND" = cpu || die "scaling is a CPU-backend experiment"
    test "$(uname -s)" = Linux || die "scaling needs Linux CPU affinity"
    cores=$(cat /sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list | sort -u | wc -l)
    smt=$(awk -F, '{ print NF }' /sys/devices/system/cpu/cpu0/topology/thread_siblings_list)
    # Cheapest arms first, so a partial ladder is still useful.
    arms="all 8x1"
    test "$smt" -ge 2 && arms="$arms 4x2"
    arms="$arms 4x1 2x1 1x1"
    for arm in $arms; do
        if [ "$arm" = all ]; then
            cpus=""; workers=""
        else
            n=${arm%x*}; s=${arm#*x}
            test "$n" -le "$cores" || continue
            cpus=$(cpu_list "$n" "$s") || die "cannot place $arm on this topology"
            workers=$((n * s))
        fi
        repeats=3
        case "$arm" in 1x1|2x1) repeats=1 ;; esac
        for mode in shape rescore combo; do
            run "$cpus" "$workers" "$DEST/scaling/$arm/panel1-$mode" --skip-existing \
                --query-limit 1 --mode "$mode" --warmups 1 --repeats "$repeats"
        done
    done
}

# Where affinity cannot be set (macOS), only the worker count varies; the OS
# places the workers. Each arm is t<N>, run like a scaling arm.
cmd_threads() {
    test "$BACKEND" = cpu || die "threads is a CPU-backend experiment"
    test -n "${R3_THREADS:-}" || die "set R3_THREADS, e.g. \"4 8 10 12 14\""
    for n in $R3_THREADS; do
        for mode in shape rescore combo; do
            run "" "$n" "$DEST/scaling/t$n/panel1-$mode" --skip-existing \
                --query-limit 1 --mode "$mode" --warmups 1 --repeats 3
        done
    done
}

case "${1:-}" in
    env) cmd_env ;;
    smoke) cmd_smoke ;;
    table) cmd_table ;;
    scaling) cmd_scaling ;;
    threads) cmd_threads ;;
    *) die "usage: $0 env|smoke|table|scaling|threads" ;;
esac
