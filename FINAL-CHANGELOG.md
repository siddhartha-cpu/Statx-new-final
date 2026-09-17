# StatNex AI changelog

- Replaced the stock template splash with a premium light StatNex AI workspace and responsive routes for Overview, AI Workspace, Documents, Competency, Results, Assessment, and Settings.
- Added secure scrypt password auth, signed httpOnly sessions, account persistence, protected API access, and cache-clearing logout.
- Added Mongo-backed conversations/messages, provider preferences, health cooldowns, encrypted Gemini OAuth token storage, and user module records.
- Added the authorized server-only StatNex AI service as the default route, while preserving optional admin-configured provider adapters and automatic failure fallback.
- Added Auto/Web/AI-only search controls, Brave/Tavily server-side search abstraction, source normalization, deduplication, and persisted citations.
- Added fallback-safe SSE delivery, neutral engine attribution, useful normalized client errors, persistent document uploads, and configurable fallback behavior.
- Simplified navigation around Overview, AI Workspace, Documents, Competency, Results, Assessment, and Settings; conversation history now lives entirely inside AI Workspace.
- Reworked Overview with colorful live counts and recent document/insight activity, replaced the header email with an interactive display-name profile, and added responsive mobile navigation.
- Fixed document uploads with multi-file selection, streamed disk storage, a persistent Docker volume, and removal of the former 5 MB application limit.
- Added the reference-video document intelligence experience with real summary, notes, flashcard, MCQ, competency, and grounded document-chat actions.
- Added persistent document Q&A bubbles, animated click-to-flip flashcards, interactive MCQs with correctness and explanations, and richer structured result typography.
- Added persistent light/dark modes across login and authenticated screens with a colorful blue, cyan, emerald, amber, and indigo palette.
- Replaced Competency with clickable document History, connected saved MCQ attempts to Results, and added PDF-based Assignments with selectable 2-, 5-, or 10-mark questions.
- Rebuilt Settings around profile and visual theme choices, and corrected dark-mode gradient contrast across Results and stat cards.
- Added Dockerfiles, Nginx SPA/API proxy, Docker Compose with persistent Mongo volume and health checks, environment templates, and deployment documentation.
- Removed platform-only Vite deployment plugins and backend integration dependency from the deployable application.