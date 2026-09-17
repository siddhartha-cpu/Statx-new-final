# Statx AI changelog

- Replaced the stock template splash with a cohesive Statx AI dark workspace and routes for Overview, AI Workspace, Conversations, Providers, Documents, Competency, Results, Assessment, and Settings.
- Added secure scrypt password auth, signed httpOnly sessions, account persistence, protected API access, and cache-clearing logout.
- Added Mongo-backed conversations/messages, provider preferences, health cooldowns, encrypted Gemini OAuth token storage, and user module records.
- Added OpenAI, Anthropic, Groq, Gemini, and local mock provider adapters with automatic eligibility routing and failure fallback.
- Added Auto/Web/AI-only search controls, Brave/Tavily server-side search abstraction, source normalization, deduplication, and persisted citations.
- Added Dockerfiles, Nginx SPA/API proxy, Docker Compose with persistent Mongo volume and health checks, environment templates, and deployment documentation.
- Removed platform-only Vite deployment plugins and backend integration dependency from the deployable application.