import client from "./client";

export function getCredentialsCatalog() {
  return client.get("/credentials/catalog");
}

export function getOAuthSetup() {
  return client.get("/credentials/oauth-setup");
}

export function getCredentialsOverview() {
  return client.get("/credentials/overview");
}

export function listCredentials(params = {}) {
  return client.get("/credentials", { params });
}

export function createCredential(body) {
  return client.post("/credentials", body);
}

export function updateCredential(id, body) {
  return client.patch(`/credentials/${id}`, body);
}

export function deleteCredential(id) {
  return client.delete(`/credentials/${id}`);
}

export function setDefaultCredential(id) {
  return client.post(`/credentials/${id}/set-default`);
}

export function verifyCredential(id) {
  return client.post(`/credentials/${id}/verify`);
}
