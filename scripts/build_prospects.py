#!/usr/bin/env python3
"""Bake public/data/prospects.json from Org Review's scraped MLB.com T30 lists.

Source of truth: Stadium-Ventures/sv-org-review (private) ->
data/prospects_top_scraped.csv. Pulled via `gh api` (needs the behrlich-sv
account active: `gh auth switch --user behrlich-sv`), or pass --csv <path>
to read a local export instead.

Usage:
    python3 scripts/build_prospects.py            # pull from GitHub
    python3 scripts/build_prospects.py --csv f.csv
"""
import argparse, csv, io, json, re, subprocess, sys
from pathlib import Path

REPO_PATH = "repos/Stadium-Ventures/sv-org-review/contents/data/prospects_top_scraped.csv"
OUT = Path(__file__).resolve().parent.parent / "public" / "data" / "prospects.json"


def parse_bonus(s):
    """'$2.90m' / '$425,000' / '' -> int dollars or None."""
    s = (s or "").strip().lower().replace(",", "").lstrip("$")
    if not s:
        return None
    m = re.fullmatch(r"([\d.]+)\s*m", s)
    try:
        return int(float(m.group(1)) * 1e6) if m else int(float(s))
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="local CSV path instead of gh api")
    args = ap.parse_args()

    if args.csv:
        text = Path(args.csv).read_text()
    else:
        text = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw", REPO_PATH],
            capture_output=True, text=True, check=True).stdout

    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        team = (row.get("team_abbrev") or "").strip()
        if not team:
            continue
        try:
            rank = int(row["rank"])
        except (KeyError, ValueError):
            continue
        out.setdefault(team, []).append({
            "rank": rank,
            "name": (row.get("name") or "").strip(),
            "pos": (row.get("pos") or "").strip().upper(),
            "level": (row.get("level") or "").strip() or None,
            "age": int(row["age"]) if (row.get("age") or "").strip().isdigit() else None,
            "eta": int(row["eta"]) if (row.get("eta") or "").strip().isdigit() else None,
            "bonus": parse_bonus(row.get("bonus")),
            "from": (row.get("signed_from") or "").strip() or None,
            "mkt": (row.get("sign_mkt") or "").strip() or None,
        })
    for team in out:
        out[team].sort(key=lambda p: p["rank"])

    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    n = sum(len(v) for v in out.values())
    print(f"wrote {OUT} — {len(out)} teams, {n} prospects")
    if len(out) != 30:
        print("WARNING: expected 30 teams", file=sys.stderr)


if __name__ == "__main__":
    main()
