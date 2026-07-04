const STORAGE_KEY = "novaflow_chat_sessions";

export function loadSessions() {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveSessions(sessions) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function upsertSession(session) {
  const sessions = loadSessions();
  const idx = sessions.findIndex((s) => s.id === session.id);
  if (idx >= 0) {
    sessions[idx] = { ...sessions[idx], ...session, updatedAt: Date.now() };
  } else {
    sessions.unshift({ ...session, updatedAt: Date.now() });
  }
  saveSessions(sessions);
  return sessions;
}

export function deleteSession(sessionId) {
  const sessions = loadSessions().filter((s) => s.id !== sessionId);
  saveSessions(sessions);
  return sessions;
}

export function getSessionsForApp(appId) {
  return loadSessions()
    .filter((s) => s.appId === appId)
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
}

export function getSessionMessages(sessionId) {
  const session = loadSessions().find((s) => s.id === sessionId);
  return session?.messages || [];
}

export function saveSessionMessages(sessionId, messages, title) {
  const sessions = loadSessions();
  const idx = sessions.findIndex((s) => s.id === sessionId);
  if (idx < 0) return sessions;
  sessions[idx].messages = messages;
  if (title) sessions[idx].title = title;
  sessions[idx].updatedAt = Date.now();
  saveSessions(sessions);
  return sessions;
}
