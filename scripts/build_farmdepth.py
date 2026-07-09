#!/usr/bin/env python3
"""Bake public/data/farmdepth.json — per-org farm system depth by position, for
the Team Fit "who's already in the pipeline at this position" read.

Source: Stadium-Ventures/sv-draft-fit public/data/farm_system_depth.json (private
repo, fetched via `gh api`). Per team: {org, full_name, total_prospects,
positions:{POS:[{name,position,raw_position,org_rank,fv,level,eta,age}]}}.

Trimmed to the 5 fields the front end actually uses (name, fv, eta, age,
org_rank) — level/position/raw_position dropped. fv/age are coerced to numbers
when cleanly numeric ("60" -> 60, "19.9" -> 19.9); FV grades with a hedge suffix
("45+") stay strings; blank strings become null. Position keys (C/1B/.../SP/
MIRP/SIRP/...) are kept as-is from the source. Team keys are normalized the same
way as build_regime.py: KCR->KC, SDP->SD, SFG->SF, TBR->TB, WSN->WSH, OAK->ATH.

Usage: python3 scripts/build_farmdepth.py
"""
import base64
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "public", "data", "farmdepth.json")

SRC_REPO = "Stadium-Ventures/sv-draft-fit"
SRC_PATH = "public/data/farm_system_depth.json"

ABBR_FIX = {"KCR": "KC", "SDP": "SD", "SFG": "SF", "TBR": "TB", "WSN": "WSH", "OAK": "ATH"}


def fetch_source():
    out = subprocess.run(
        ["gh", "api", f"repos/{SRC_REPO}/contents/{SRC_PATH}", "--jq", ".content"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(base64.b64decode(out))


def norm_abbr(a):
    return ABBR_FIX.get(a, a)


def coerce(v):
    """blank -> None; cleanly-numeric string -> int/float; else left as-is."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        try:
            f = float(s)
            return int(f) if f.is_integer() else f
        except ValueError:
            return s
    return v


def main():
    raw = fetch_source()
    out = {}
    for team, rec in raw.items():
        positions = {}
        for pos, plist in rec.get("positions", {}).items():
            positions[pos] = [
                {
                    "name": p.get("name"),
                    "fv": coerce(p.get("fv")),
                    "eta": coerce(p.get("eta")),
                    "age": coerce(p.get("age")),
                    "org_rank": coerce(p.get("org_rank")),
                }
                for p in plist
            ]
        out[norm_abbr(team)] = {
            "total_prospects": rec.get("total_prospects"),
            "positions": positions,
        }

    assert len(out) == 30, f"expected 30 teams, got {len(out)}"
    total = sum(v["total_prospects"] for v in out.values())

    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    kb = os.path.getsize(OUT) // 1024
    print(f"wrote {OUT} ({kb} KB) — {len(out)} teams, {total} prospects league-wide")
    sample_team = "KC" if "KC" in out else next(iter(out))
    sample = out[sample_team]
    breakdown = {pos: len(plist) for pos, plist in sample["positions"].items()}
    print(f"sample {sample_team}: total_prospects={sample['total_prospects']} breakdown={breakdown}")


if __name__ == "__main__":
    main()
