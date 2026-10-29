#!/usr/bin/env python3
"""Export the agent-development record that the paper counts and plots.

This runs against the private development repositories and writes a sanitized
snapshot under runs/archive/agent-development-record/. The paper build reads
only that snapshot, never the repositories.

The snapshot deliberately omits ticket titles, branch and worktree paths, and
decision titles: they name internal hosts, private corpora, and filesystem
layout. What remains is the shape of the record -- ids, epochs, model tiers,
dates, dependencies -- which is what the figure and the counts need.

Sources:
  --repo       the ROSHAMBO3 development repository, read at --ref
  --origin     the ROSHAMBO2 fork where the ticket system began (2026-08-15);
               tickets T01-T48 were created there and migrated on 2026-08-20
  --side-repo  optional extra repositories whose commits count toward
               activity (the separate Apple workspace)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# The two tier vocabularies are aliases (tickets/CONVENTIONS.md, "Model
# names -- two hierarchies"). Normalize to one for plotting, keep the raw value.
TIER_ALIASES = {"astra": "fable", "sol": "opus", "terra": "sonnet", "luna": "haiku"}
# Some later tickets name a model rather than a tier word, e.g. gpt-6.1-sol-high;
# its tier is the tier word inside the name.
MODEL_TIER = re.compile(r"gpt-[0-9.]+-(astra|sol|terra|luna)(?:-[a-z]+)?")


# Tickets whose frontmatter names the agent system rather than the model. The
# model comes from the session logs; the ticket itself stays as written, since
# CONVENTIONS.md forbids rewriting frontmatter.
MODEL_OVERRIDES = {
    "T82": "gpt-5.6-terra",  # frontmatter says `codex`; the session logs show GPT 5.6-Terra
}


def tier_of(name: str) -> str:
    if (m := MODEL_TIER.fullmatch(name)):
        name = m.group(1)
    return TIER_ALIASES.get(name, name)

# Epochs are contiguous id ranges; the boundaries are where the work changed
# subject, read from the ticket record. Upper bounds are inclusive.
EPOCHS = [
    (48, "plan", "Plan and GPU baseline"),
    (116, "gpu", "GPU field, color, accuracy"),
    (152, "cpu-port", "CPU port"),
    (168, "cpu-color", "CPU color"),
    (177, "divergence", "Engine divergence, web app"),
    (224, "cpu-combo", "CPU combo"),
    (254, "native", "Native x86 and ARM"),
    (266, "metal", "Metal"),
    (280, "hardening", "Release hardening"),
    (303, "format3", "Corpus format 3"),
    (10**9, "release", "Re-verification and release"),
]

TICKET_FIELDS = [
    "id", "number", "epoch", "lane", "status", "model", "model_tier",
    "reviewer", "reviewer_tier", "created", "closed", "depends_on",
    "retroactive", "reopened",
]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match is None:
        raise ValueError("ticket has no frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        item = re.match(r"^([a-z_]+):\s*(.*?)\s*(?:#.*)?$", line)
        if item:
            fields[item.group(1)] = item.group(2)
    return fields


def id_list(value: str) -> list[str]:
    return [token for token in re.split(r"[,\s\[\]]+", value or "") if token]


def epoch_of(number: int) -> str:
    for upper, key, _ in EPOCHS:
        if number <= upper:
            return key
    raise AssertionError("unreachable")


def status_events(log: str) -> list[tuple[str, str]]:
    """(date, status) for every `+status:` line in a `git log -p` stream."""
    events, date = [], None
    for line in log.splitlines():
        if line.startswith("@@C "):
            date = line.split()[1]
        elif date and (m := re.match(r"^\+status:\s*([a-z-]+)", line)):
            events.append((date, m.group(1)))
    return sorted(events)


def origin_history(origin: Path, ticket: str) -> tuple[list[str], str | None, list[tuple[str, str]]]:
    """Creation dates, the move into tickets/closed/, and status events in ROSHAMBO2."""
    pattern = f":(glob)tickets/**/{ticket}-*.md"
    created, closed_move = [], None
    current = None
    names = git(origin, "log", "--all", "--format=@@C %aI", "--name-status", "--", pattern)
    for line in names.splitlines():
        if line.startswith("@@C "):
            current = line.split()[1]
            continue
        parts = line.split("\t")
        if parts[0] == "A" and current:
            created.append(current)
        if (parts[0].startswith("R") and len(parts) == 3
                and "/closed/" in parts[2] and "/closed/" not in parts[1]):
            closed_move = min(filter(None, [closed_move, current]))
    patches = git(origin, "log", "--all", "--format=@@C %aI", "-p", "--", pattern)
    return created, closed_move, status_events(patches)


def ticket_record(repo: Path, ref: str, origin: Path, path: str) -> dict:
    fields = frontmatter(git(repo, "show", f"{ref}:{path}"))
    ticket = fields["id"].strip()
    number = int(ticket[1:])
    pattern = f":(glob)tickets/{ticket}-*.md"

    created = git(repo, "log", "--all", "--diff-filter=A", "--format=%aI", "--", pattern).split()
    origin_created, origin_closed, origin_events = origin_history(origin, ticket)
    created = sorted(created + origin_created)

    events = sorted(origin_events + status_events(
        git(repo, "log", ref, "--format=@@C %aI", "-p", "--", pattern)))
    status = fields.get("status", "").strip()
    closed = None
    if status == "closed":
        candidates = [d for d, s in events if s == "closed"] + ([origin_closed] if origin_closed else [])
        if not candidates:
            # Some closures landed only inside merge commits.
            merged = status_events(git(repo, "log", ref, "-m", "--format=@@C %aI", "-p", "--", pattern))
            candidates = [d for d, s in merged if s == "closed"]
        if not candidates:
            raise ValueError(f"{ticket} is closed but no closing transition was found")
        closed = min(candidates)

    seen_closed, reopened = False, False
    for _, value in events:
        if value == "closed":
            seen_closed = True
        elif seen_closed and value in ("open", "claimed", "in-review"):
            reopened = True

    model = fields.get("model", "").strip()
    reviewer = fields.get("reviewer", "").strip()
    return {
        "id": ticket,
        "number": number,
        "epoch": epoch_of(number),
        "lane": fields.get("lane", "").strip().replace("host/IO", "host-io"),
        "status": status,
        "model": model,
        "model_tier": tier_of(MODEL_OVERRIDES.get(ticket, model)),
        "reviewer": reviewer,
        "reviewer_tier": tier_of(reviewer),
        "created": created[0] if created else "",
        "closed": closed or "",
        "depends_on": " ".join(id_list(fields.get("depends_on", ""))),
        "retroactive": str(fields.get("retroactive", "").strip() == "true").lower(),
        "reopened": str(reopened).lower(),
    }


def commit_days(repo: Path, ref: str, origin: Path, side_repos: list[Path], migrated: str) -> list[dict]:
    """Commits per UTC day: the repository at ref, ROSHAMBO2 before the migration."""
    def day_counts(repo_path: Path, *args: str) -> Counter:
        stamps = git(repo_path, "log", *args, "--format=%H %aI").splitlines()
        unique = {line.split()[0]: line.split()[1] for line in stamps if line}
        return Counter(
            datetime.fromisoformat(stamp).astimezone(timezone.utc).date().isoformat()
            for stamp in unique.values()
        )

    columns = {
        "repository": day_counts(repo, ref),
        "origin": day_counts(origin, "--all", "--since=2026-08-15T00:00:00Z", f"--until={migrated}"),
    }
    for index, side in enumerate(side_repos):
        columns[f"side{index}"] = day_counts(side, "--all")
    days = sorted(set().union(*columns.values()))
    return [{"date": day, **{name: counts.get(day, 0) for name, counts in columns.items()}} for day in days]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--origin", type=Path, required=True)
    parser.add_argument("--side-repo", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    commit = git(args.repo, "rev-parse", args.ref).strip()
    tree = git(args.repo, "ls-tree", "-r", "--name-only", commit).splitlines()
    ticket_paths = sorted(p for p in tree if re.fullmatch(r"tickets/T\d+-[^/]*\.md", p))
    decisions = sorted(
        m.group(1) for p in tree if (m := re.fullmatch(r"decisions/(D\d+)-[^/]*\.md", p)))

    records = sorted(
        (ticket_record(args.repo, commit, args.origin, path) for path in ticket_paths),
        key=lambda record: record["number"],
    )
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ticket ids")
    for record in records:
        missing = [d for d in record["depends_on"].split() if d not in ids]
        if missing:
            raise ValueError(f"{record['id']} depends on unknown tickets {missing}")

    conventions = git(args.repo, "show", f"{commit}:tickets/CONVENTIONS.md")
    section = re.search(r"^## Numbered pitfalls\s*$\n(.*?)(?=^## |\Z)", conventions,
                        flags=re.MULTILINE | re.DOTALL)
    if section is None:
        raise ValueError("CONVENTIONS.md has no numbered-pitfall section")
    pitfalls = sorted(int(n) for n in re.findall(r"^(\d+)\. ", section.group(1), re.MULTILINE))

    migrated = git(args.repo, "log", "--max-parents=0", "--format=%aI", commit).split()[0]
    days = commit_days(args.repo, commit, args.origin, args.side_repo, migrated)

    args.output.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=TICKET_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    (args.output / "tickets.csv").write_text(buffer.getvalue(), encoding="utf-8")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(days[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(days)
    (args.output / "commit-days.csv").write_text(buffer.getvalue(), encoding="utf-8")

    record = {
        "generator": "scripts/export_development_record.py",
        "source_commit": commit,
        "exported_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "origin_migration_utc": migrated,
        "epochs": [{"key": key, "label": label, "last_ticket": upper if upper < 10**9 else None}
                   for upper, key, label in EPOCHS],
        "tier_aliases": TIER_ALIASES,
        "decisions": decisions,
        "pitfalls": pitfalls,
        "commit_day_columns": {
            "repository": "commits reachable from source_commit",
            "origin": "ROSHAMBO2 fork, all refs, from 2026-08-15 until the migration",
            **{f"side{i}": "separate Apple workspace, all refs" for i in range(len(args.side_repo))},
        },
    }
    (args.output / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} tickets, {len(decisions)} decisions, {len(pitfalls)} pitfalls, "
          f"{len(days)} commit days to {args.output}")


if __name__ == "__main__":
    main()
