import client from "./client";

export async function getIntegrationSettings() {
  return client.get("/integrations/settings");
}

export async function updateIntegrationSettings(payload) {
  return client.patch("/integrations/settings", payload);
}

export async function getIntegrationHealth() {
  return client.get("/integrations/health");
}

export async function verifyTelegramBot(payload = {}) {
  return client.post("/integrations/telegram/verify", payload);
}

export async function registerTelegramWebhook(payload) {
  return client.post("/integrations/telegram/register-webhook", payload);
}

export async function testEmailIntegration(payload = {}) {
  return client.post("/integrations/email/test", payload);
}

export async function getTelegramWebhookStatus() {
  return client.get("/integrations/telegram/webhook-status");
}

export async function testNotify(payload) {
  return client.post("/integrations/notify/test", payload);
}

export async function getTelegramSetup(workflowId) {
  return client.get(`/integrations/telegram/setup/${workflowId}`);
}

export function startGmailOAuth() {
  const params = new URLSearchParams();
  const token = typeof window !== "undefined" ? localStorage.getItem("nf_token") : "";
  const wid = typeof window !== "undefined" ? localStorage.getItem("nf_workspace_id") : "";
  if (token) params.set("t", token);
  if (wid) params.set("workspace_id", wid);
  const qs = params.toString();
  window.location.href = `/api/v1/integrations/gmail/oauth/start${qs ? `?${qs}` : ""}`;
}

export async function disconnectGmailOAuth() {
  return client.post("/integrations/gmail/oauth/disconnect");
}

export async function verifyJira() {
  return client.post("/integrations/jira/verify");
}

export async function testSlackIntegration(payload = {}) {
  return client.post("/integrations/slack/test", payload);
}

export async function verifyGithub() {
  return client.post("/integrations/github/verify");
}

export async function testDiscordIntegration(payload = {}) {
  return client.post("/integrations/discord/test", payload);
}

export async function verifyLinear() {
  return client.post("/integrations/linear/verify");
}

export async function bindSlackEvents(payload) {
  return client.post("/integrations/slack/events/bind", payload);
}
