// MLBAM team id -> abbreviation. The /api/v1/draft feed gives team.id + team.name
// but NO abbreviation; our other SV data (teamintel, org-review) is keyed by abbrev,
// so this map is the join key. Abbrevs match sv-teamintel conventions (KC, SD, WSH...).
const ID_TO_ABBR = {
  108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC", 113: "CIN",
  114: "CLE", 115: "COL", 116: "DET", 117: "HOU", 118: "KC",  119: "LAD",
  120: "WSH", 121: "NYM", 133: "ATH", 134: "PIT", 135: "SD",  136: "SEA",
  137: "SF",  138: "STL", 139: "TB",  140: "TEX", 141: "TOR", 142: "MIN",
  143: "PHI", 144: "ATL", 145: "CHW", 146: "MIA", 147: "NYY", 158: "MIL",
};

// schoolClass from the feed -> coarse bucket used for org-tendency matching.
function classBucket(schoolClass) {
  if (!schoolClass) return "UNK";
  const c = schoolClass.toUpperCase();
  if (c.startsWith("HS")) return "HS";
  if (c.startsWith("JC")) return "JUCO";
  if (c.startsWith("4YR")) return "4YR";
  return "OTHER"; // e.g. "NS" (non-student / international)
}

function abbr(teamId) {
  return ID_TO_ABBR[teamId] || null;
}

module.exports = { ID_TO_ABBR, abbr, classBucket };
