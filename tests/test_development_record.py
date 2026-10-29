"""The exported development record agrees with the shipped research record.

Every field of runs/archive/agent-development-record that a ticket's frontmatter
determines is recomputed here from the release's tickets/, decisions/ and
tickets/CONVENTIONS.md. Dates, reopen events and commit counts come from git
history, which the release does not ship; those stay as exported.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RECORD = ROOT / "runs/archive/agent-development-record"
RELEASE = ROOT.parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


export = load_module("export_development_record", ROOT / "scripts/export_development_record.py")


@unittest.skipUnless((RELEASE / "tickets/CONVENTIONS.md").is_file(),
                     "the research record is not shipped beside publication/")
class ShippedRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (RECORD / "tickets.csv").open(encoding="utf-8", newline="") as handle:
            cls.rows = {row["id"]: row for row in csv.DictReader(handle)}
        cls.record = json.loads((RECORD / "record.json").read_text(encoding="utf-8"))
        cls.shipped = {}
        for path in sorted((RELEASE / "tickets").glob("T*.md")):
            if re.fullmatch(r"T\d+-[^/]*\.md", path.name):
                fields = export.frontmatter(path.read_text(encoding="utf-8"))
                cls.shipped[fields["id"].strip()] = fields

    def test_same_tickets(self):
        self.assertEqual(sorted(self.rows), sorted(self.shipped))

    def test_frontmatter_fields_match(self):
        for ticket, fields in self.shipped.items():
            row = self.rows[ticket]
            model = fields.get("model", "").strip()
            reviewer = fields.get("reviewer", "").strip()
            expected = {
                "epoch": export.epoch_of(int(ticket[1:])),
                "lane": fields.get("lane", "").strip().replace("host/IO", "host-io"),
                "status": fields.get("status", "").strip(),
                "model": model,
                "model_tier": export.tier_of(export.MODEL_OVERRIDES.get(ticket, model)),
                "reviewer": reviewer,
                "reviewer_tier": export.tier_of(reviewer),
                "depends_on": " ".join(export.id_list(fields.get("depends_on", ""))),
                "retroactive": str(fields.get("retroactive", "").strip() == "true").lower(),
            }
            with self.subTest(ticket=ticket):
                self.assertEqual({key: row[key] for key in expected}, expected)
                # A closed ticket has a closing date; an open one does not.
                self.assertEqual(bool(row["closed"]), expected["status"] == "closed")

    def test_decisions_and_pitfalls_match(self):
        decisions = sorted(
            m.group(1) for path in (RELEASE / "decisions").glob("D*.md")
            if (m := re.fullmatch(r"(D\d+)-[^/]*\.md", path.name)))
        self.assertEqual(self.record["decisions"], decisions)
        conventions = (RELEASE / "tickets/CONVENTIONS.md").read_text(encoding="utf-8")
        section = re.search(r"^## Numbered pitfalls\s*$\n(.*?)(?=^## |\Z)", conventions,
                            flags=re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(section)
        pitfalls = sorted(int(n) for n in re.findall(r"^(\d+)\. ", section.group(1), re.MULTILINE))
        self.assertEqual(self.record["pitfalls"], pitfalls)


class TierTests(unittest.TestCase):
    def test_model_names_resolve_to_their_tier(self):
        self.assertEqual(export.tier_of("sol"), "opus")
        self.assertEqual(export.tier_of("gpt-6.1-sol-high"), "opus")
        self.assertEqual(export.tier_of("gpt-6.1-luna-medium"), "haiku")
        self.assertEqual(export.tier_of("opus"), "opus")
        self.assertEqual(export.tier_of("gpt-5.6-terra"), "sonnet")
        self.assertEqual(export.tier_of(export.MODEL_OVERRIDES["T82"]), "sonnet")


if __name__ == "__main__":
    unittest.main()
