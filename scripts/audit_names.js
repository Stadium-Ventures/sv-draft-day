#!/usr/bin/env node
// Name-resolution audit: does every SV client (teamintel feed) join to the
// composite board under the alias-aware normName (lib/names.js)? An unmatched
// client gets no push notification and no board highlight on draft day.
// Also flags joins that only work BECAUSE of the alias layer (so we know it's
// earning its keep) and suggests last-name candidates for hard misses —
// candidates go into public/data/aliases.json "players".
//   node scripts/audit_names.js

const fs = require("fs");
const path = require("path");
const { normName, baseNorm } = require("../lib/names");

const TEAMINTEL_URL = "https://sv-teamintel.vercel.app/teamintel.json";

(async () => {
  const composite = JSON.parse(fs.readFileSync(path.join(__dirname, "../public/data/composite.json"), "utf8"));
  const byKey = new Map(composite.map((p) => [normName(p.name), p]));
  const byBase = new Map(composite.map((p) => [baseNorm(p.name), p]));

  const res = await fetch(TEAMINTEL_URL, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`teamintel ${res.status}`);
  const ti = await res.json();
  const records = Array.isArray(ti) ? ti : (ti.records || []);
  const clients = [...new Map(records.filter((r) => r.player).map((r) => [normName(r.player), r.player])).entries()];

  let ok = 0; const aliasSaves = [], misses = [];
  for (const [key, display] of clients) {
    const hit = byKey.get(key);
    if (hit) {
      ok++;
      if (!byBase.get(baseNorm(display))) aliasSaves.push(`${display} -> ${hit.name}`);
      continue;
    }
    const last = key.split(" ").pop();
    const cands = composite.filter((p) => normName(p.name).split(" ").pop() === last).map((p) => p.name);
    misses.push({ display, key, cands });
  }

  console.log(`SV clients in teamintel feed: ${clients.length}`);
  console.log(`Matched to composite: ${ok}`);
  if (aliasSaves.length) console.log(`\nJoined ONLY thanks to the alias layer:\n  ${aliasSaves.join("\n  ")}`);
  if (misses.length) {
    console.log(`\nUNMATCHED clients (no push, no board highlight):`);
    for (const m of misses) {
      console.log(`  ${m.display}  (key: "${m.key}")`);
      if (m.cands.length) console.log(`    same last name on board: ${m.cands.join(", ")} -> add to aliases.json players if same person`);
    }
    console.log(`\nNote: a client who isn't in the media composite at all (NR client) is a legitimate miss here.`);
  } else {
    console.log("All clients join. ✓");
  }
})().catch((e) => { console.error("audit failed:", e.message || e); process.exit(1); });
