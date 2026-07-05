const SETUP_KEY = "nf_setup_complete";

export function isSetupComplete() {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(SETUP_KEY) === "1";
}

export function markSetupComplete() {
  if (typeof window === "undefined") return;
  localStorage.setItem(SETUP_KEY, "1");
}

export function resetSetup() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SETUP_KEY);
}
