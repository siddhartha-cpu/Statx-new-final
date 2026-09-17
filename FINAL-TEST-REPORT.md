# Statx AI test report

## Tests executed

- Backend import check with `python -c 'import server'`.
- Public `/api/health` and `/api/ready` checks, including a negative protected-route case.
- Frontend strict TypeScript check with `yarn typecheck`.
- Frontend production build with `yarn build`.
- Public browser happy path: registration/login, dashboard, provider view, new conversation, prompt send, conversation persistence, and navigation.
- Docker Compose configuration parse and image-build readiness review.
- Full browser/backend verification suite: iteration 2 reported 11 passed, 0 failed, and no bugs.

## Credential boundary

The workspace has no real OpenAI, Anthropic, Groq, Gemini OAuth, Brave, or Tavily credentials. Live provider calls and OAuth token exchange are therefore **NOT LIVE-TESTED**. Local chat smoke uses `DEMO_MODE=true`, explicitly labeled as a MOCK provider. Search is not claimed live without `SEARCH_API_KEY` or `TAVILY_API_KEY`.

The public smoke returned `health=ok`, `ready=ready`, and the unauthenticated conversations check returned `401`. Frontend typecheck and production build passed. Python compilation/import passed. Docker CLI/image build was **NOT RUN** because the validation environment does not provide a Docker executable; the Compose file was structurally parsed with PyYAML and includes health checks plus a persistent Mongo volume.

## Known limitations

- Gemini OAuth token exchange, encrypted token persistence, and access-token refresh are implemented but must be exercised with a real Google OAuth client in deployment.
- Streaming transport is prepared around safe pre-response provider selection, but the current workspace UI uses a persisted JSON response so fallback cannot occur after partial output.