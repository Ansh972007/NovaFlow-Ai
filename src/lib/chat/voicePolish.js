/**
 * Polish voice transcripts into clearer sendable text.
 */

const FILLERS = /\b(um+|uh+|erm+|ah+|like|you know)\b/gi;

const WORD_FIXES = [
  [/\bimpliment(ing|ed|s)?\b/gi, "implement$1"],
  [/\bfor mr\b/gi, "for me"],
  [/\bfor mee\b/gi, "for me"],
  [/\bcan you do this for mr\b/gi, "can you do this for me"],
  [/\bon this subjects\b/gi, "on this subject"],
  [/\be-?\s*mail\b/gi, "email"],
  [/\bgovern ment\b/gi, "government"],
  [/\bdaly\b/gi, "daily"],
  [/\bcredenti?als?\b/gi, "credentials"],
  [/\baprov+e\b/gi, "approve"],
  [/\bdeplo+y\b/gi, "deploy"],
];

/**
 * Convert spoken email fragments into an address when possible.
 * e.g. "alex at gmail dot com" → alex@gmail.com
 */
export function polishSpokenEmail(text) {
  let t = String(text || "");
  // already has @
  if (/[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}/i.test(t)) {
    return t;
  }
  t = t.replace(
    /\b([a-z0-9._%+\-]+)\s+at\s+([a-z0-9\-]+)\s+dot\s+([a-z]{2,})\b/gi,
    (_, user, domain, tld) => `${user}@${domain}.${tld}`,
  );
  t = t.replace(
    /\b([a-z0-9._%+\-]+)\s+at\s+([a-z0-9.\-]+\.[a-z]{2,})\b/gi,
    (_, user, host) => `${user}@${host}`,
  );
  return t;
}

function capitalizeSentences(text) {
  const s = String(text || "").trim();
  if (!s) return "";
  return s.replace(/(^|[.!?]\s+)([a-z])/g, (_, p, c) => p + c.toUpperCase());
}

/**
 * @param {string} raw
 * @returns {string}
 */
export function polishVoiceTranscript(raw) {
  let t = String(raw || "").replace(/\s+/g, " ").trim();
  if (!t) return "";

  t = t.replace(FILLERS, " ");
  t = t.replace(/\s+/g, " ").trim();

  for (const [pat, rep] of WORD_FIXES) {
    t = t.replace(pat, rep);
  }

  t = polishSpokenEmail(t);

  // Light punctuation: if no terminal punct and looks like a sentence
  if (t.length > 12 && !/[.!?]$/.test(t) && /\b(can you|please|i need|i want|send|email)\b/i.test(t)) {
    t = `${t}.`;
  }

  t = capitalizeSentences(t);
  // Ensure leading capital
  if (t && /^[a-z]/.test(t)) {
    t = t.charAt(0).toUpperCase() + t.slice(1);
  }
  return t.replace(/\s+/g, " ").trim();
}
