# SSO / OAuth setup

NovaFlow supports **Google** and **Microsoft** sign-in when client credentials are configured on the API server.

## Environment variables

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
MICROSOFT_CLIENT_ID=your-azure-app-id
MICROSOFT_CLIENT_SECRET=your-secret
OAUTH_REDIRECT_BASE=http://localhost:3001
FRONTEND_URL=http://localhost:3000
```

| Variable | Description |
|----------|-------------|
| `OAUTH_REDIRECT_BASE` | Public URL of the **API** (where OAuth providers redirect back) |
| `FRONTEND_URL` | Web app URL (receives JWT after successful OAuth) |

## Redirect URIs to register

Add these exact callback URLs in each provider console:

```
{OAUTH_REDIRECT_BASE}/api/v1/auth/oauth/google/callback
{OAUTH_REDIRECT_BASE}/api/v1/auth/oauth/microsoft/callback
```

Examples for local dev:

- `http://localhost:3001/api/v1/auth/oauth/google/callback`
- `http://localhost:3001/api/v1/auth/oauth/microsoft/callback`

## Google Cloud Console

1. Create OAuth 2.0 Client ID (Web application)
2. Add authorized redirect URI above
3. Copy Client ID and Secret into `backend/.env`
4. Restart API — **Google** button appears on login

## Microsoft Entra ID (Azure)

1. App registrations → New registration
2. Redirect URI: Web → callback URL above
3. Certificates & secrets → New client secret
4. API permissions: `openid`, `email`, `profile`, `User.Read`
5. Copy Application (client) ID and secret into env
6. Restart API — **Microsoft** button appears on login

## Flow

1. User clicks Google/Microsoft on login
2. API redirects to provider
3. Provider redirects to API callback
4. API creates/links user, issues JWT
5. Browser lands on `/login/oauth-callback?token=...` → Chat

## Notes

- OAuth users get **editor** role by default
- Existing accounts link by matching **email**
- SSO-only users cannot change password in Settings (use SSO)
- Admin: **Settings → Single sign-on** shows active providers
