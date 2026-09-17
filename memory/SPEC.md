# Statx AI living spec

Statx AI is a unified, dark Swiss-style AI workspace. Users create an account, choose eligible AI routing nodes, open persistent conversations, and ask questions through an automatic provider router. The router retries another eligible provider before returning output, records cooldown health, and preserves the original conversation context. Auto mode detects current-information intent; Web mode requires a configured legitimate search provider and attaches normalized source links; AI-only never searches.

## Data model

- `users`: UUID, email, scrypt password hash, display name, setup flag
- `provider_preferences`: user-selected provider order and fallback flag
- `provider_connections`: encrypted Gemini OAuth tokens only
- `provider_health`: per-user/provider cooldown and last success/error timestamps
- `conversations` + `messages`: persistent threads, provider attribution, fallback notices, citations
- `module_items`: user-owned Documents, Competency, Results, and Assessment records

## Auth and roles

There is one user role in this MVP. Registration/login issues a signed, httpOnly `statx_session` cookie. Logout clears it and the frontend clears the TanStack Query cache. `SESSION_SECRET` and `TOKEN_ENCRYPTION_KEY` are deployment secrets.

## Key flows

1. `/login` registers or signs in, then routes to `/app`.
2. `/app/providers` separates selection from authorization. Gemini uses official Google OAuth when configured; OpenAI, Anthropic, and Groq use server-only API credentials.
3. `/app/workspace` creates a conversation and sends prompts to `/api/conversations/{id}/messages` with Auto/Web/AI-only mode.
4. Current/search intent calls the configured Brave/Tavily adapter first; AI synthesis receives normalized sources and stores citations.
5. Provider errors mark a cooldown and the router attempts the next configured provider before returning a clean error.