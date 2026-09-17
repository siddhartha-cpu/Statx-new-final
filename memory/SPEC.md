# StatNex AI living spec

StatNex AI is a premium document-intelligence and chat workspace. Users create an account, upload one or many documents, run real AI actions (summary, notes, flashcards, MCQs, competency, and document Q&A), and keep general conversations in the AI Workspace. The internal server-only router can retry an admin-configured secondary route before returning output without exposing vendor or credential details.

## Data model

- `users`: UUID, email, scrypt password hash, display name, setup flag
- `provider_preferences`: neutral engine selection and fallback flag
- `provider_connections`: encrypted Gemini OAuth tokens only
- `provider_health`: per-user/provider cooldown and last success/error timestamps
- `conversations` + `messages`: persistent threads, provider attribution, fallback notices, citations
- `module_items`: user-owned Documents, Competency, Results, and Assessment records; uploaded document files stream to `UPLOAD_DIR` and metadata persists in MongoDB

## Auth and roles

There is one user role in this MVP. Registration/login issues a signed, httpOnly `statx_session` cookie. Logout clears it and the frontend clears the TanStack Query cache. `SESSION_SECRET` and `TOKEN_ENCRYPTION_KEY` are deployment secrets.

## Key flows

1. `/login` registers or signs in, then routes to `/app`.
2. `/app/workspace` owns general chat and conversation history in one screen; the former standalone engine and conversation routes redirect here.
3. Prompts go to `/api/conversations/{id}/messages/stream` with Auto/Web/AI-only mode. Providers complete and fallback before SSE bytes are released.
4. Current/search intent calls the configured Brave/Tavily adapter first; AI synthesis receives normalized sources and stores citations.
5. Engine errors mark a cooldown and the router attempts the next admin-configured route before returning a clean error.
6. `/app/documents` accepts multiple PDF, DOCX, Markdown, CSV, and text files in one selection with no application-level size cap. Files use the persistent `statx-uploads` Docker volume.
7. A selected document opens the video-inspired three-column intelligence workspace: document list, AI action/result area, and persistent grounded document Q&A.
8. Flashcards render as animated click-to-flip decks. MCQs render as clickable options with immediate correctness, the right answer, a document-grounded explanation, and a save-to-Results action.
9. History replaces Competency and owns the clickable uploaded-document timeline plus every saved AI action. Results shows automatically saved MCQ scores and AI-graded assignment submissions with improvement feedback.
10. Assignments lists uploaded PDFs, generates homework at 2-, 5-, or 10-mark difficulty, supports print/save-as-PDF, accepts a completed PDF, and grades it through the server AI route.
11. The overview summarizes chat history, uploaded documents, History, and exam Results. The header shows the account display name, not its email address.
12. Light and dark modes are available on login and authenticated screens, stored under `statnex-theme`; Settings provides visual Light, Dark, and Automatic theme cards without technical backend copy.
13. Settings accepts JPG, PNG, or WebP profile and banner images. Files persist under `UPLOAD_DIR`, image endpoints require the account session, and the profile photo appears in the global header.