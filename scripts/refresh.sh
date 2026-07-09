#!/usr/bin/env bash
# Re-bake the hub's data from the latest sources (composite_latest.csv, org-review
# xlsx, MLB slot order, leverage) and deploy. Run after updating the composite.
set -e
cd "$(dirname "$0")/.."
echo "▸ rebuilding data…"
python3 scripts/build_data.py
python3 scripts/build_homegrown.py
python3 scripts/build_prospects.py
python3 scripts/build_warhist.py   # WAR lookback + debut speed; reads public/data/aWAR.xlsx (--awar to override)
python3 scripts/build_regime.py    # front-office regime windows (sv-draft-fit)
python3 scripts/build_farmdepth.py # positional farm depth w/ FV (sv-draft-fit)
python3 scripts/build_projection.py # NCAA projectability, board-filtered (ncaa-baseball-models)
python3 scripts/build_draftdb.py   # 2021-25 merged draft DB, slim (sv-draft-fit)
if git diff --quiet public/data; then
  echo "✓ no data changes — nothing to deploy."
  exit 0
fi
git add public/data
git commit -m "Refresh data $(date +%F)"
git push
echo "✓ pushed — Vercel auto-deploys in ~30s."
