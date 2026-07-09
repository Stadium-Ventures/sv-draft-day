// Draft-console "Ask the data" endpoint.
// The client packs a compact snapshot of the draft-day system (draft status, pools,
// client book, slot-history aggregates) and sends a freeform question; we relay it
// to the Claude API and return the answer. Server-side only — the API key never
// reaches the browser.
//
//   POST /api/ask  { question, context } -> { answer, usage }

const API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = "claude-sonnet-5";
const MAX_CONTEXT_BYTES = 80 * 1024;   // hard cap on client-packed context

const SYSTEM = `You are the analytics desk inside a baseball agency's MLB Draft war room, live on draft day.
The user is an agent advising drafted-and-draftable clients on signing bonuses, slot values, and leverage.
The DRAFT DATA in the message is split into tagged sections — [DRAFT-STATUS], [POOLS], [CLIENTS],
[PICK-#5 HISTORY 2018-25], [TEAM MIN], and the like. Hard rules:
- Answer ONLY from those tagged sections. Never estimate, extrapolate, or fill gaps from memory.
- After every number or fact, cite the section tag it came from in brackets, e.g. "($8.34M [POOLS])".
- If no section covers what's asked, say plainly "not in the provided data" and name what's missing.
Keep the war-room tone: direct, quantitative, tight — a few sentences or a short list, read on a console mid-draft.`;

// Oversized context: drop whole trailing sections (a line starting with "[" opens a section)
// until it fits — never a raw byte slice that cuts a section mid-row.
function truncateContext(context, maxBytes) {
  if (Buffer.byteLength(context, "utf8") <= maxBytes) return context;
  const sections = []; let cur = [];
  for (const ln of context.split("\n")) {
    if (ln.startsWith("[") && cur.length) { sections.push(cur.join("\n")); cur = []; }
    cur.push(ln);
  }
  if (cur.length) sections.push(cur.join("\n"));
  let dropped = 0;
  while (sections.length > 1 && Buffer.byteLength(sections.join("\n"), "utf8") > maxBytes) { sections.pop(); dropped++; }
  return sections.join("\n") + `\n[TRUNCATED: ${dropped} sections dropped]`;
}

module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method not allowed" });
  if (!API_KEY) return res.status(500).json({ error: "ANTHROPIC_API_KEY not configured" });

  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
    const question = (body.question || "").trim();
    if (!question) return res.status(400).json({ error: "question required" });
    const context = truncateContext(String(body.context || ""), MAX_CONTEXT_BYTES);

    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 1500,
        system: SYSTEM,
        messages: [{ role: "user", content: `DRAFT DATA\n${context}\n\nQuestion: ${question}` }],
      }),
    });
    const data = await r.json();
    if (!r.ok) {
      const msg = data?.error?.message || `upstream ${r.status}`;
      return res.status(502).json({ error: msg });
    }
    if (data.stop_reason === "refusal") return res.status(200).json({ answer: "(request declined by the model)", usage: data.usage });
    const answer = (data.content || []).filter(b => b.type === "text").map(b => b.text).join("\n") || "(no answer)";
    return res.status(200).json({ answer, usage: data.usage, model: data.model });
  } catch (err) {
    return res.status(500).json({ error: String(err.message || err) });
  }
};
module.exports.truncateContext = truncateContext;   // exported for tests
