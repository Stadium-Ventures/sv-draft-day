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

## Season on/off — reactivate for 2027, archive after

This project is built to sit dormant between drafts and get switched back on for
the next one. There's a single client-side kill switch (`LIVE_POLLING` in
`public/index.html`, right above the bootstrap IIFE at the bottom of the
`<script>` block) that gates every recurring poll — the draft clock (3s), shared
intel (12s), teamintel (15s), pick-in-play (15s), and X leads (20s). The one-shot
loads on page open stay on regardless, so the site always renders the last known
board even while `LIVE_POLLING` is `false`.

**Reactivate before a draft:**
1. Flip `LIVE_POLLING` to `true` in `public/index.html` and push.
2. Bump the year in `api/draft.js`, `api/reported.js`, `api/xlead.js`
   (`YEAR`/`DEFAULT_YEAR` constants) and `scripts/build_data.py` /
   `scripts/build_projection.py` (`DRAFT_YEAR`/`TARGET_YEAR`).
3. Re-provision Vercel env vars: `REDIS_URL`, `SITE_PASSWORD`,
   `ANTHROPIC_API_KEY`, VAPID keys (push), and — only if the X-lead feed is
   wanted again — `DRAFTDAY_SHEET_CSV_URL` (or `DRAFTDAY_SHEET_ID`),
   `DD_INGEST_KEY`, `DD_POLL_SECONDS`. `/api/xlead` and `/api/xlead-ingest`
   stay dormant on their own until these are set, regardless of `LIVE_POLLING`.
4. If using X leads, re-deploy the Google Apps Script trigger
   (`scripts/sv_draftday_capture_v1.0.0.gs`) and the browser watcher
   (`scripts/sv_x_watcher.user.js`).
5. Refresh `public/data/*.json` for the new year via `scripts/refresh.sh` /
   `scripts/build_data.py`.
6. Smoke-test with `vercel dev` before opening the war room.

**Archive right after the draft:**
1. Flip `LIVE_POLLING` back to `false` in `public/index.html` and push — this
   alone stops the recurring client polling that drives most Vercel usage.
2. Disable the Apps Script trigger and the userscript watcher if X leads were
   in use, so nothing keeps feeding the (now-unpolled) sheet.
3. Optional deeper cleanup: unset `DRAFTDAY_SHEET_CSV_URL`/`DD_INGEST_KEY`/
   `ANTHROPIC_API_KEY` in Vercel so `/api/xlead*` 200-noop even if something
   still hits them directly.
