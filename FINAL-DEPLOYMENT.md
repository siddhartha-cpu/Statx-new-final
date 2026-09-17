# StatNex AI deployment

## Step 1 — Upload

Upload this repository to a Docker-capable VPS and copy `backend/.env.example` to `backend/.env`.

## Step 2 — Configure environment variables

Required for production:

- `MONGO_URL`, `DB_NAME`
- `CORS_ORIGINS`, `FRONTEND_URL`, `APP_ENV=production`
- `SESSION_SECRET` (long random value)
- `TOKEN_ENCRYPTION_KEY` (a valid Fernet key)
- `UPLOAD_DIR=/data/uploads` for persistent document storage
- `EMERGENT_LLM_KEY` for the authorized server-side StatNex AI service; the platform may inject this automatically
- Optional `ENGINE_MODEL` (defaults to `gpt-5.4`)
- At least one live-search configuration for current-information answers: `SEARCH_PROVIDER=brave` and `SEARCH_API_KEY`, or `SEARCH_PROVIDER=tavily` and `TAVILY_API_KEY`

Optional admin-only provider routes (not required from end users):

- OpenAI: `OPENAI_API_KEY`, optional `OPENAI_MODEL`
- Anthropic: `ANTHROPIC_API_KEY`, optional `ANTHROPIC_MODEL`
- Groq: `GROQ_API_KEY`, optional `GROQ_MODEL`
- Gemini OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, optional `GEMINI_MODEL`. Register the callback as `https://your-domain.example/api/providers/gemini/callback` in the Google OAuth web client.
- Brave Search: `SEARCH_PROVIDER=brave`, `SEARCH_API_KEY`, optional `SEARCH_ENDPOINT`; optional `SEARCH_PROVIDER_FALLBACK=tavily` and `TAVILY_API_KEY`.

Set `DEMO_MODE=false` in production. Never put the AI Engine key, provider keys, OAuth tokens, or search credentials in frontend variables, browser storage, API responses, or logs.

## Step 3 — Deploy

Run `docker compose up -d --build`. MongoDB persists in `statx-mongo`; uploaded documents persist in `statx-uploads`. The backend creates indexes automatically on startup, and the frontend reverse proxy serves the SPA plus `/api` on port 80.

## Step 4 — Open website

Open the host URL and create a StatNex AI account. General chat and document intelligence use the authorized server-side AI service immediately; ordinary users do not configure provider credentials.

The application can run behind a normal TLS reverse proxy. Use the public HTTPS origin for `FRONTEND_URL`, `CORS_ORIGINS`, and the Google redirect URI.