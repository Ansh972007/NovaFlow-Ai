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
