import { getApiBaseUrl } from "./config";

export function getSamlStatus() {
  return fetch(`${getApiBaseUrl().replace(/\/$/, "")}/api/v1/auth/saml/status`)
    .then((r) => r.json())
    .then((d) => (d.status_code === 200 ? d.data : { enabled: false }));
}

export function startSamlLogin() {
  const base = getApiBaseUrl().replace(/\/$/, "");
  window.location.href = `${base}/api/v1/auth/saml/start`;
}
