#!/usr/bin/env node
// Bake the SV player registry (be-sv-repo/data/players/*.json — the hand-curated client
// dossiers) into public/data/svregistry.json for the draft-history card's SV badge.
// Canonical dossiers only: <slug>.json with no dot in the slug and no leading underscore
// (sidecars like <slug>.live_state.json are skipped, per that repo's SCHEMA.md). Coaches
// are excluded — the badge marks players. Match on identity.full_name + aliases, never
// the slug (display names prefer nicknames; slugs are frozen legacy keys).
// Usage: node scripts/build_svregistry.js   (override source with SV_REGISTRY_DIR)
const fs = require("fs"), path = require("path");
const { normName } = require("../lib/names.js");

// Default source is the canonical org registry (Stadium-Ventures/sv-registry);
// ~/be-sv-repo was the pre-migration personal home and is defunct as a source.
const SRC = process.env.SV_REGISTRY_DIR
  || [
    path.join("/workspace", "sv-registry", "data", "players"),
    path.join(process.env.HOME || "", "sv-registry", "data", "players"),
    path.join(process.env.HOME || "", "be-sv-repo", "data", "players"),
  ].find((p) => fs.existsSync(p));
if (!SRC) {
  console.error("build_svregistry: no registry checkout found — set SV_REGISTRY_DIR to sv-registry/data/players");
  process.exit(1);
}
const OUT = path.join(__dirname, "..", "public", "data", "svregistry.json");

const files = fs.readdirSync(SRC).filter(f =>
  f.endsWith(".json") && !f.startsWith("_") && !f.slice(0, -5).includes("."));

const names = {};
let players = 0;
for (const f of files) {
  let d;
  try { d = JSON.parse(fs.readFileSync(path.join(SRC, f), "utf8")); } catch (e) { continue; }
  const id = d.identity || d;
  const cs = d.current_state || {};
  // SV Way agency-status rule: representation is checked FIRST — a former
  // client (is_client:false — Orf, Glavine, ...) must never badge as SV.
  if (cs.is_client === false) continue;
  // Coaches are excluded by the canonical field (current_state.tier), not the
  // legacy role string — tier is what the registry itself keys careers on.
  const role = d.role || cs.role || id.role;
  if (cs.tier === "coach" || String(role || "").toLowerCase() === "coach") continue;
  const full = id.full_name; if (!full) continue;
  players++;
  for (const n of [full, ...(id.aliases || [])]) {
    const k = normName(n);
    if (k) names[k] = full;
  }
}

fs.writeFileSync(OUT, JSON.stringify({ built: new Date().toISOString().slice(0, 10),
  source: SRC, players, names }, null, 1));
console.log(`svregistry.json: ${players} players, ${Object.keys(names).length} name keys`);
