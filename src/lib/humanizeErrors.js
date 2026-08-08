/** Short, user-facing messages for technical API / SMTP / OAuth errors. */

export function humanizeCredentialError(raw) {
  const s = String(raw || "").trim();
  if (!s) return "Verification failed. Check your settings and try again.";

  const low = s.toLowerCase();

  if (low.includes("username and password not accepted") || low.includes("badcredentials") || s.includes("535")) {
    return "Gmail rejected the login. Use a Google App Password or connect with “Connect with Google”.";
  }
  if (low.includes("invalid_grant") || low.includes("token refresh failed")) {
    return "Google OAuth expired or was revoked. Reconnect with Google.";
  }
  if (low.includes("invalid api key") || low.includes("incorrect api key") || low.includes("401")) {
    return "API key was rejected. Double-check the key in Credentials.";
  }
  if (low.includes("403") || low.includes("forbidden") || low.includes("access denied")) {
    return "Access denied. Check account permissions or reconnect OAuth.";
  }
  if (low.includes("timeout") || low.includes("timed out")) {
    return "Connection timed out. Check host, port, and network.";
  }
  if (low.includes("smtp user and password required")) {
    return "Enter your email address and App Password.";
  }
  if (low.includes("connect gmail") || low.includes("refresh token")) {
    return "Connect Gmail with Google OAuth or paste a refresh token.";
  }
  if (s.startsWith("(535,") || low.includes("gsmtp")) {
    return "Email login failed. For Gmail, use an App Password or OAuth.";
  }

  if (s.length > 140) return `${s.slice(0, 140)}…`;
  return s;
}

export function humanizeFinetuneError(raw) {
  const s = String(raw || "").trim();
  if (!s) return "Training failed. Check your OpenAI API key and dataset.";

  const low = s.toLowerCase();

  if (low.includes("openrouter") || (low.includes("404") && low.includes("fine_tuning"))) {
    return "OpenRouter cannot train models. Add a native OpenAI API key under Credentials → AI / Models.";
  }
  if (low.includes("401") || low.includes("invalid api key") || low.includes("incorrect api key")) {
    return "OpenAI rejected the API key. Add a valid key in Credentials → AI / Models.";
  }
  if (low.includes("no api key")) {
    return "No API key found. Add an OpenAI key in Credentials before training.";
  }
  if (low.includes("dataset needs at least one row")) {
    return "Dataset is empty. Generate a dataset with at least one Q&A row.";
  }
  if (low.includes("quota") || low.includes("rate limit")) {
    return "OpenAI rate limit or quota hit. Wait a moment or check your OpenAI billing.";
  }

  if (s.length > 160) return `${s.slice(0, 160)}…`;
  return s;
}
