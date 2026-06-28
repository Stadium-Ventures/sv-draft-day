# SV Draft Day

One hub for the war room on July 11–12, 2026. Live picks, a round-aware clock,
team interest (teamintel), composite rankings, org tendencies, and bonus-pool
tracking — desktop and mobile. Mock-draft mode for rehearsal (fast-follow).

Stack: vanilla static + Vercel serverless + Upstash Redis (same as `sv-draft-cards`,
shares `REDIS_URL`). Zero build step on purpose — least to break on draft day.

## Live data spine

`/api/draft` proxies MLB's official tracker feed:

    https://statsapi.mlb.com/api/v1/draft/2026   (year overridable: ?year=2025)

It normalizes the rounds→picks tree into a flat ordered board, derives **on the
clock** (first pick with `isDrafted == false`), and computes per-team bonus pools.
Results cache in Redis ~2s so a war room of devices polling every 3s coalesces to
~1 upstream fetch. Falls back to direct fetch if `REDIS_URL` is unset.

Feed fields we rely on: `pickNumber`, `pickRound`, `roundPickNumber`, `team.id`
(→ abbrev via `lib/teams.js`; the feed has no abbreviation), `pickValue` (slot),
`signingBonus`, `person.fullName/id`, `school.name/schoolClass` (→ HS/4YR/JUCO).

## Status

- [x] **Phase 0** — live spine (`/api/draft`) + On The Clock screen, verified vs 2025/2026 feeds
- [ ] Phase 1 — On The Clock fully loaded (countdown tuning, team panel)
- [ ] Phase 2 — `scripts/build_data.py`: composite rankings + org tendencies + teamintel → `public/data/*.json`; name-match join live picks → board
- [ ] Phase 3 — Our Clients + Bonus Pools views (v1 pillars)
- [ ] Phase 4 — Mock-draft mode (sim feed + auto-pick + manual override)

## Data sources (joined in Phase 2)

| Source | Path | Key |
|---|---|---|
| Composite rankings | `~/Desktop/claude/draft-rankings-composite/outputs/composite_latest.csv` | name |
| Org review (pools, slots, 30yr tendencies) | `~/Desktop/claude/sv-org-review/Org.Review.2026.update_*.xlsx` | team abbrev |
| Team interest / PDWs | `https://sv-teamintel.vercel.app/teamintel.json` (CORS-open) | player + team abbrev |
| Client roster | `sv-draft-cards` Redis `draftcard:roster` | slug |

## Local dev

    npm install
    REDIS_URL=... vercel dev        # or run without REDIS_URL (direct-fetch fallback)

## Deploy

Vercel project + `REDIS_URL` env var (reuse the sv-teamintel / sv-draft-cards
Upstash instance). Auto-deploy from git push.
