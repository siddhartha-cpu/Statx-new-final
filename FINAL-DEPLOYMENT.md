# Statx AI deployment

## Step 1 — Upload

Upload this repository to a Docker-capable VPS and copy `backend/.env.example` to `backend/.env`.

## Step 2 — Configure environment variables

Required for production:

- `MONGO_URL`, `DB_NAME`
- `CORS_ORIGINS`, `FRONTEND_URL`, `APP_ENV=production`
- `SESSION_SECRET` (long random value)
- `TOKEN_ENCRYPTION_KEY` (a valid Fernet key)
- At least one AI route: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, or Gemini OAuth variables
- At least one live-search configuration for current-information answers: `SEARCH_PROVIDER=brave` and `SEARCH_API_KEY`, or `SEARCH_PROVIDER=tavily` and `TAVILY_API_KEY`

Provider-specific:

- OpenAI: `OPENAI_API_KEY`, optional `OPENAI_MODEL`
- Anthropic: `ANTHROPIC_API_KEY`, optional `ANTHROPIC_MODEL`
- Groq: `GROQ_API_KEY`, optional `GROQ_MODEL`
- Gemini OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, optional `GEMINI_MODEL`. Register the callback as `https://your-domain.example/api/providers/gemini/callback` in the Google OAuth web client.
- Brave Search: `SEARCH_PROVIDER=brave`, `SEARCH_API_KEY`, optional `SEARCH_ENDPOINT`; optional `SEARCH_PROVIDER_FALLBACK=tavily` and `TAVILY_API_KEY`.

Set `DEMO_MODE=false` in production. Never put provider keys in frontend variables or browser storage.

## Step 3 — Deploy

Run `docker compose up -d --build`. MongoDB persists in the `statx-mongo` volume. The backend creates indexes automatically on startup, and the frontend reverse proxy serves the SPA plus `/api` on port 80.

## Step 4 — Open website

Open the host URL, create a Statx account, select providers, and connect Gemini only through the Google OAuth button. OpenAI, Anthropic, and Groq become eligible when their server credentials are configured.

The application can run behind a normal TLS reverse proxy. Use the public HTTPS origin for `FRONTEND_URL`, `CORS_ORIGINS`, and the Google redirect URI.