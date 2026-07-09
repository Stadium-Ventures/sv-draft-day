#!/usr/bin/env python3
"""Bake public/data/projection.json — a per-player projectability/caliber layer
merged from the NCAA hitter + pitcher models (private repo
Stadium-Ventures/ncaa-baseball-models), keyed by normalized player name so the
board (public/index.html) can join it straight onto composite.json rows.

Sources (private, not vendored — pull via git blob API, large files):
  gh api "repos/Stadium-Ventures/ncaa-baseball-models/git/trees/HEAD?recursive=1" \
      --jq '.tree[]|select(.path=="NCAA_Hitter_Model_Latest.csv")|.sha'
  gh api repos/Stadium-Ventures/ncaa-baseball-models/git/blobs/$sha --jq '.content' \
      | base64 -d > /tmp/ncaa_hitter.csv
  (same for NCAA_Pitcher_Model_Latest.csv)

Method:
  - Each source row is a player-season. Per playerFullName, keep the row whose
    Draft_Eligible_Year == 2026 if present, else the row with the max
    Draft_Eligible_Year (most recent read on that player).
  - Hitters carry Final_Weighted_FV / Model_Tier; pitchers carry Final_FV and
    have NO Model_Tier column in the source — tier stays null for pitchers
    rather than fabricated. Pitcher tool Z-scores (Z_FB/Z_Perf/Z_K_minus_BB/
    Z_Miss/Z_BB_Flag) are renamed to velo/perf/k_bb/miss/bb_flag.
  - If a normalized name appears in BOTH files (rare — shared names or a
    two-way player), the hitter row wins as the primary record and the pitcher
    tool set is merged in under the same entry (kind:"both") rather than dropped.
  - normName mirrors public/index.html's normName exactly (lowercase, NFD-strip
    accents, punctuation -> space, strip Jr/Sr/II-V suffix tokens, keep a-z +
    spaces, collapse whitespace).
  - FILTERED to the board: only players on public/data/composite.json ship
    (the app pushes public/data/* to every war-room device — the full 25k-name
    model layer is ~7MB, the board slice is a few hundred KB). Output entries
    are RE-KEYED by the COMPOSITE player's normName so the front end joins with
    zero fuzz at runtime. Two light fuzzy fallbacks recover name-variant misses
    for otherwise-unmatched College players (each match is logged for review):
      (a) initial-collapse: "a j evasco" <-> "aj evasco" on both sides
      (b) first-name prefix: same last token + one first token is a >=3-char
          prefix of the other (chris/christopher, kam/kamden), requiring a
          school-word overlap when both sides carry school words.

Usage: python3 scripts/build_projection.py [--hitter path.csv] [--pitcher path.csv]
"""
import argparse, csv, json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "public", "data", "projection.json")
COMPOSITE = os.path.join(ROOT, "public", "data", "composite.json")

DEFAULT_HITTER = "/tmp/ncaa_hitter.csv"
DEFAULT_PITCHER = "/tmp/ncaa_pitcher.csv"
TARGET_YEAR = 2026

SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?")


def norm_name(s):
    """Mirror public/index.html normName exactly."""
    s = (s or "").strip()
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[.'’`\-]", " ", s)
    s = SUFFIX.sub("", s)
    s = re.sub(r"[^a-z\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def collapse_initials(key):
    """'a j evasco' -> 'aj evasco': merge runs of single-letter tokens."""
    out, run = [], []
    for tok in key.split():
        if len(tok) == 1:
            run.append(tok)
        else:
            if run:
                out.append("".join(run)); run = []
            out.append(tok)
    if run:
        out.append("".join(run))
    return " ".join(out)


SCHOOL_STOP = {"university", "of", "college", "the", "state", "at", "a", "m",
               "hs", "prep", "school", "academy", "and"}


def school_words(s):
    """Significant lowercase words from a school string (composite school
    strings carry ', City ST' hometowns — drop them)."""
    s = (s or "").split(",")[0]
    return {w for w in norm_name(s).split() if w not in SCHOOL_STOP and len(w) > 1}


def to_num(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_pct(s):
    if s is None or s == "":
        return None
    s = s.strip().rstrip("%")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def pick_latest(rows):
    """rows for one player: prefer Draft_Eligible_Year==TARGET_YEAR, else max."""
    target, best, best_year = None, None, None
    for r in rows:
        y = to_num(r.get("Draft_Eligible_Year"))
        if y is None:
            continue
        if int(y) == TARGET_YEAR:
            target = r
        if best_year is None or y > best_year:
            best_year, best = y, r
    return target or best


def load_model(path, kind):
    """kind 'hit' | 'pit'. Returns dict: normName -> entry."""
    by_name = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = row.get("playerFullName", "").strip()
            if name:
                by_name.setdefault(norm_name(name), []).append(row)

    out = {}
    for key, rows in by_name.items():
        r = pick_latest(rows)
        if r is None:
            continue
        if kind == "hit":
            out[key] = {
                "final_fv": to_num(r.get("Final_Weighted_FV")),
                "tier": (r.get("Model_Tier") or "").strip() or None,
                "draftProb": to_pct(r.get("Draft_Prob_Pct")),
                "top2Prob": to_pct(r.get("Top2_Prob_Pct")),
                "kind": "hit",
                "school": (r.get("school") or "").strip() or None,
                "tools": {
                    "pwr": to_num(r.get("Z_Pwr")),
                    "cont": to_num(r.get("Z_Cont")),
                    "disc": to_num(r.get("Z_Disc")),
                    "speed": to_num(r.get("Z_Speed")),
                },
            }
        else:
            out[key] = {
                "final_fv": to_num(r.get("Final_FV")),
                "tier": None,  # source pitcher CSV has no Model_Tier column
                "draftProb": to_pct(r.get("Draft_Prob_Pct")),
                "top2Prob": to_pct(r.get("Top2_Prob_Pct")),
                "kind": "pit",
                "school": (r.get("newestTeamName") or "").strip() or None,
                "tools": {
                    "velo": to_num(r.get("Z_FB")),
                    "perf": to_num(r.get("Z_Perf")),
                    "k_bb": to_num(r.get("Z_K_minus_BB")),
                    "miss": to_num(r.get("Z_Miss")),
                    "bb_flag": to_num(r.get("Z_BB_Flag")),
                },
            }
    return out


def merge(hitters, pitchers):
    out = dict(hitters)
    both = 0
    for key, p in pitchers.items():
        if key in out:
            entry = out[key]
            entry["kind"] = "both"
            entry["pitcher_tools"] = p["tools"]
            entry["pitcher_final_fv"] = p["final_fv"]
            both += 1
        else:
            out[key] = p
    return out, both


def fuzzy_find(comp_key, comp_school, projection):
    """Fuzzy fallbacks for one unmatched composite College player.
    Returns (source_key, how) or (None, None)."""
    # (a) initial-collapse on both sides
    collapsed = {collapse_initials(k): k for k in projection}
    ck = collapse_initials(comp_key)
    if ck in collapsed:
        return collapsed[ck], "initials"

    # (b) first-name-prefix: same last token, first tokens prefix-related (>=3
    # chars), school-word overlap required when both sides have school words.
    ct = comp_key.split()
    if len(ct) < 2:
        return None, None
    c_first, c_last = ct[0], ct[-1]
    c_sch = school_words(comp_school)
    candidates = []
    for k, entry in projection.items():
        st = k.split()
        if len(st) < 2 or st[-1] != c_last:
            continue
        s_first = st[0]
        a, b = sorted((c_first, s_first), key=len)
        if len(a) < 3 or not b.startswith(a):
            continue
        s_sch = school_words(entry.get("school"))
        if c_sch and s_sch and not (c_sch & s_sch):
            continue
        candidates.append(k)
    if len(candidates) == 1:
        return candidates[0], "prefix"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hitter", default=DEFAULT_HITTER)
    ap.add_argument("--pitcher", default=DEFAULT_PITCHER)
    args = ap.parse_args()

    hitters = load_model(args.hitter, "hit")
    pitchers = load_model(args.pitcher, "pit")
    projection, both = merge(hitters, pitchers)

    with open(COMPOSITE, encoding="utf-8") as fh:
        comp = json.load(fh)

    out = {}
    exact = 0
    fuzzy_log = []
    unmatched = []
    college_total = college_hit = 0
    for p in comp:
        name = p.get("name", "")
        level = p.get("level", "")
        key = norm_name(name)
        if not key or key in out:
            continue
        if level == "College":
            college_total += 1
        if key in projection:
            out[key] = projection[key]
            exact += 1
            if level == "College":
                college_hit += 1
            continue
        if level == "College":
            src, how = fuzzy_find(key, p.get("school"), projection)
            if src:
                out[key] = projection[src]
                fuzzy_log.append((name, src, how))
                college_hit += 1
                continue
        unmatched.append(f"{name} [{level}]")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))

    print(f"wrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")
    print(f"source pool: {len(hitters)} hitters + {len(pitchers)} pitchers "
          f"-> {len(projection)} merged ({both} hit+pit name collisions)")
    print(f"board slice: {len(out)} entries / {len(comp)} composite players "
          f"({exact} exact + {len(fuzzy_log)} fuzzy)")
    print(f"College join rate: {college_hit}/{college_total} "
          f"({100*college_hit/max(college_total,1):.1f}%)")

    if fuzzy_log:
        print("\nfuzzy matches (composite -> source):")
        for cname, skey, how in fuzzy_log:
            print(f"  [{how}] {cname} -> {skey}")

    print(f"\nunmatched composite players: {len(unmatched)}")
    for n in unmatched[:15]:
        print(f"  - {n}")

    sample_key = next(iter(out))
    print(f"\nsample entry [{sample_key}]: {json.dumps(out[sample_key])}")


if __name__ == "__main__":
    main()
