"""Tests for the portability run importer."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "import_portability", ROOT / "scripts" / "import_portability.py")
importer = importlib.util.module_from_spec(SPEC)
sys.modules["import_portability"] = importer
SPEC.loader.exec_module(importer)


class ImportTests(unittest.TestCase):
    def test_cloud_fqdn_is_shortened_everywhere(self):
        self.assertEqual(importer.shorten('"host": "vm-1.zone-x1-c.c.some-project.internal"'),
                         '"host": "vm-1"')
        self.assertEqual(importer.shorten("lock.vm-1.zone-x1-c.c.some-project.internal.GPU-ab"),
                         "lock.vm-1.GPU-ab")
        self.assertEqual(importer.shorten("roci and lock.roci.GPU-ab"), "roci and lock.roci.GPU-ab")

    def test_paths_and_gpu_uuids_are_redacted(self):
        # Fixture strings are assembled at run time so this file itself carries
        # no literal local path or device identifier for the release audit.
        home, users, data = "/" + "home/u", "/" + "Users/me", "/" + "data/user/x"
        uuid = "GPU-" + "deadbeef-0000-0000-0000-000000000000"
        text = (f'{{"corpus": "{home}/corpora/LIT-PCBA", "src": "{users}/r3bench/src", '
                f'"data": "{data}/y.sdf", "uuid": "{uuid}", '
                f'"lock": "/tmp/roshambo3.gpu.lock.roci.{uuid}", '
                f'"url": "file://{home}/r3bench/src", "pip": "roshambo3 @ file://{users}/src", '
                '"host": "roci", "rel": "runs/portability/x.json", "sha": "ab12"}')
        out = importer.shorten(text)
        for leaked in (home, users, data, "deadbeef"):
            self.assertNotIn(leaked, out)
        self.assertIn('"corpus": "$EXTERNAL_DATA"', out)
        self.assertIn('"url": "file://$EXTERNAL_DATA"', out)
        self.assertIn("[device identifier removed]", out)
        for kept in ('"host": "roci"', '"rel": "runs/portability/x.json"', '"sha": "ab12"'):
            self.assertIn(kept, out)

    def test_macos_hardware_identifiers_are_redacted(self):
        profile = json.dumps({"SPHardwareDataType": [{
            "serial_number": "C02FAKE000", "platform_UUID": "00000000-0000-0000-0000-000000000000",
            "provisioning_UDID": "00000000-0000000000000000", "number_processors": "proc 14:10:4"}],
            "SPDisplaysDataType": [{"sppci_cores": "20", "spdisplays_ndrvs": [
                {"_spdisplays_display-serial-number": "fake0000"}]}]}, indent=2)
        env = json.dumps({"system_profiler": profile})
        out = json.loads(json.loads(importer.shorten(env))["system_profiler"])
        hardware = out["SPHardwareDataType"][0]
        for key in ("serial_number", "platform_UUID", "provisioning_UDID"):
            self.assertEqual(hardware[key], "[device identifier removed]")
        display = out["SPDisplaysDataType"][0]
        self.assertEqual(display["spdisplays_ndrvs"][0]["_spdisplays_display-serial-number"],
                         "[device identifier removed]")
        # Counts the portability analysis reads are untouched.
        self.assertEqual(hardware["number_processors"], "proc 14:10:4")
        self.assertEqual(display["sppci_cores"], "20")
        # Metal registry ids: the numeric field and the lock identity built from it.
        registry = "4" + "000000001"
        record = json.dumps({"locks": [{"backend": "metal", "identity": "metal-" + registry}],
                             "device": {"registry_id": int(registry), "sppci_cores": "20"}})
        for text in (record, json.dumps({"embedded": record})):
            out = importer.shorten(text)
            self.assertNotIn(registry, out)
            out = json.loads(out)
            if "embedded" in out:
                out = json.loads(out["embedded"])
            self.assertEqual(out["locks"][0]["identity"], "[device identifier removed]")
            self.assertEqual(out["device"]["registry_id"], "[device identifier removed]")
            self.assertEqual(out["device"]["sppci_cores"], "20")

    def test_nvidia_smi_board_serial_is_redacted(self):
        smi = ("Product Name : NVIDIA L4\n    Serial Number : 0000000000001\n"
               "    GPU PDI : 0x00000000000001\n    FB Memory Usage\n")
        out = json.loads(importer.shorten(json.dumps({"nvidia_smi": smi})))["nvidia_smi"]
        self.assertIn("Serial Number : [device identifier removed]", out)
        self.assertIn("GPU PDI : [device identifier removed]", out)
        self.assertIn("Product Name : NVIDIA L4", out)

    def test_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            out, runs = Path(temp) / "out" / "dev", Path(temp) / "runs"
            (out / "table").mkdir(parents=True)
            (out / "scaling" / "1x1").mkdir(parents=True)
            (out / "table" / "panel8-shape.json").write_text(json.dumps({"h": "a.b.c.p.internal"}))
            (out / "scaling" / "1x1" / "panel1-shape.csv").write_text("x\n")
            (out / "table" / "notes.md").write_text("OUT=" + "/" + "home/u/x\n")
            (out / "env.json").write_text("{}")
            sys.argv = ["import", str(out), "--runs", str(runs)]
            importer.main()
            self.assertEqual(json.loads((runs / "portability/dev/panel8-shape.json").read_text()),
                             {"h": "a"})
            self.assertTrue((runs / "portability-scaling/dev/1x1/panel1-shape.csv").is_file())
            self.assertTrue((runs / "portability/dev/env.json").is_file())
            self.assertEqual((runs / "portability/dev/notes.md").read_text(), "OUT=$EXTERNAL_DATA\n")


if __name__ == "__main__":
    unittest.main()
