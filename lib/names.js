// Shared player-name resolution — the server-side twin of index.html's normName.
// Base normalization (lowercase, strip diacritics/suffixes/punctuation) plus the
// alias layer from public/data/aliases.json: initials merging ("j t ginn" ->
// "jt ginn"), first-name diminutive folding (mike -> michael), and explicit
// per-player aliases (org-review legal names -> common names, "austin wood" ->
// "gage wood"). Keep the base logic byte-identical to index.html's baseNorm.

const aliases = require("../public/data/aliases.json");

const SUFFIX = /\b(jr|sr|ii|iii|iv|v)\b/g;
const baseNorm = (s) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/[.'’`\-]/g, " ").replace(SUFFIX, "").replace(/[^a-z\s]/g, " ").replace(/\s+/g, " ").trim();

// merge runs of single-letter tokens so "J.T. Ginn" and "JT Ginn" key the same
const mergeInitials = (b) => b.replace(/\b([a-z]) (?=[a-z]\b)/g, "$1");

const NICK = {};
for (const g of aliases.nickGroups || []) for (let i = 1; i < g.length; i++) NICK[g[i]] = g[0];
const PLAYERS = {};
for (const [k, v] of Object.entries(aliases.players || {})) PLAYERS[mergeInitials(baseNorm(k))] = mergeInitials(baseNorm(v));

function normName(s) {
  let b = mergeInitials(baseNorm(s));
  if (PLAYERS[b]) b = PLAYERS[b];
  const i = b.indexOf(" ");
  if (i > 0) {
    const t0 = NICK[b.slice(0, i)];
    if (t0) { b = t0 + b.slice(i); if (PLAYERS[b]) b = PLAYERS[b]; }
  }
  return b;
}

module.exports = { normName, baseNorm };
