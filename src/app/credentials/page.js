import CredentialsClient from "./CredentialsClient";

export const metadata = {
  title: "Credentials — NovaFlow AI",
  description: "API keys, models, Gmail, Telegram, and integration secrets",
};

export default function CredentialsPage() {
  return <CredentialsClient />;
}
