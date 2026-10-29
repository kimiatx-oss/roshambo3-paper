#!/usr/bin/env python3
"""Copy one device's portability_campaign.sh output into runs/.

    python scripts/import_portability.py <campaign out>/<DEVICE_KEY>

table/ and env.json go to runs/portability/<key>/, scaling/ to
runs/portability-scaling/<key>/, smoke/ to runs/portability-smoke/<key>/.

Every text file is redacted on the way in, with the release policy's text
rules (scripts/release_policy.py) and nothing else:

* local paths under /home, /data, /mnt, and macOS /Users become $EXTERNAL_DATA,
  including pip's file:// install URLs;
* GPU UUIDs, and hardware identifiers (nvidia-smi and system_profiler serial
  numbers, nvidia-smi GPU PDIs, platform UUIDs, UDIDs, MAC addresses, Metal
  registry ids and the `metal-<registry id>` lock identity), become
  "[device identifier removed]";
* cloud VM host names, fully qualified with the cloud project and zone
  (`<host>.<zone>.c.<project>.internal`), are shortened to the host name.

Host names themselves, hashes, fingerprints, and hit lists are kept: the
portability analyses compare them.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

CLOUD_FQDN = re.compile(r"(?<=[A-Za-z0-9-])\.[a-z0-9-]+\.c\.[a-z0-9-]+\.internal")
# The release policy's patterns, with macOS home directories added.
LOCAL_PATH = re.compile(r'(?<![\w./:])/(?:home|data|mnt|Users)/(?:[^\s"\'<>`{}(),;\\]+)')
GPU_ID = re.compile(r"GPU-[0-9a-fA-F-]{30,}")
# pip records the install source as a file:// URL, which LOCAL_PATH's
# look-behind (no preceding "/" or ":") deliberately does not match.
FILE_URL = re.compile(r'file://(?=/(?:home|data|mnt|Users)/)[^\s"\'<>`{}(),;\\]+')
# Hardware identifiers, mirroring release_policy.py's hardware_identifiers():
# serials (system_profiler, nvidia-smi "Serial Number"), nvidia-smi "GPU PDI",
# platform/hardware UUIDs, UDIDs, MAC addresses and machine-id, as "key": "value",
# key: value or "key" = "value". A JSON document embedded as a string (env.json)
# escapes its quotes. GPU UUIDs are GPU_ID's. The value must contain a digit and
# be 6+ characters, so placeholders and code are left alone.
_HW_KEY = (r'(?:serial(?:[_ -]?number)?|platform[_ -]?uuid|provisioning[_ -]?udid|'
           r'hardware[_ -]?uuid|ioplatform(?:serialnumber|uuid)|machine[_-]?id|'
           r'board[_ -]?serial|mac[_ -]?address|pdi)')
HARDWARE_KV = re.compile(
    r'(?<![A-Za-z0-9])(?:\\?["\'])?(?P<key>[A-Za-z0-9_-]*' + _HW_KEY + r')(?:\\?["\'])?(?![\w-])'
    r'(?:[ \t]*\([^)\n]*\))?[ \t]*[:=][ \t]*(?:\\?["\'])?(?P<value>[A-Za-z0-9][A-Za-z0-9:_.-]*)', re.I)
HARDWARE_BARE_SERIAL = re.compile(
    r'(?i:serial)[^\n]{0,30}?(?<![A-Za-z0-9])(?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])(?P<value>[A-Z0-9]{10,12})(?![A-Za-z0-9])')
HARDWARE_IOREG = re.compile(
    r'\\?"(?P<key>IOPlatform\w*(?:Serial|UUID|UDID|ID)\w*)\\?"\s*=\s*(?:\\?")?(?P<value>[A-Za-z0-9][A-Za-z0-9:_.-]*)')
# Metal device registry ids: numeric JSON values (re-quoted as a string so the
# JSON stays valid) and the lock identity built from them, "metal-<digits>".
METAL_REGISTRY_ID = re.compile(
    r'(?P<q>\\?")(?P<key>registry[_-]?id)(?P=q)(?P<sep>[ \t]*:[ \t]*)\d{6,}(?![\d.])', re.I)
METAL_IDENTITY = re.compile(r"(?<![A-Za-z0-9])metal-\d{6,}(?!\d)")
REMOVED = "[device identifier removed]"


def hardware_identifiers(text: str) -> list[str]:
    found = []
    for rx in (HARDWARE_KV, HARDWARE_IOREG):
        for m in rx.finditer(text):
            value = m.group("value").strip()
            if (len(value) >= 6 and re.search(r"\d", value) and not value.upper().startswith("GPU-")
                    and value.lower() not in {"unknown", "none", "null", "n/a"}):
                found.append(value)
    found += [m.group("value") for m in HARDWARE_BARE_SERIAL.finditer(text)]
    return sorted(set(found), key=len, reverse=True)
LAYOUT = {"table": "portability", "scaling": "portability-scaling", "smoke": "portability-smoke"}


def shorten(text: str) -> str:
    """Redact one text file (see the module docstring)."""
    text = CLOUD_FQDN.sub("", text)
    text = FILE_URL.sub("file://$EXTERNAL_DATA", text)
    text = LOCAL_PATH.sub("$EXTERNAL_DATA", text)
    text = METAL_REGISTRY_ID.sub(
        lambda m: f"{m['q']}{m['key']}{m['q']}{m['sep']}{m['q']}{REMOVED}{m['q']}", text)
    text = METAL_IDENTITY.sub(REMOVED, text)
    for value in hardware_identifiers(text):
        text = text.replace(value, REMOVED)
    return GPU_ID.sub(REMOVED, text)


def copy_tree(source: Path, destination: Path) -> int:
    count = 0
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:  # every text file is redacted, whatever its suffix (.md, .out, .tsv, ...)
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            shutil.copy2(path, target)
        else:
            target.write_text(shorten(text), encoding="utf-8")
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("device_dir", type=Path)
    parser.add_argument("--runs", type=Path, default=Path("runs"))
    args = parser.parse_args()
    key = args.device_dir.name
    for part, runs_dir in LAYOUT.items():
        source = args.device_dir / part
        if source.is_dir():
            n = copy_tree(source, args.runs / runs_dir / key)
            print(f"{key}: {n} files from {part}/ -> {args.runs / runs_dir / key}")
    env = args.device_dir / "env.json"
    if env.is_file():
        destination = args.runs / "portability" / key / "env.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(shorten(env.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main()
