# Adaptive IT Learning Path Guide

An adaptive IT learning platform that combines a structured, module-based learning path with a
Retrieval-Augmented Generation (RAG) AI tutor and progress tracking.

Developed for **Lusail University — College of Information Technology**, ITCC 403 Graduation
Project (Academic Year 2025/2026).

> **Project Title:** Adaptive IT Learning Path Guide with AI Tutor
> **Supervisor:** Dr. Ouarda Bettaz

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
  - [Implemented](#implemented)
  - [Planned / Not Yet Implemented](#planned--not-yet-implemented)
- [RAG Pipeline](#rag-pipeline)
- [Diagnostic Assessment & Adaptive Path](#diagnostic-assessment--adaptive-path)
- [Pages & Screens](#pages--screens)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [Quick Start (automated scripts)](#quick-start-automated-scripts)
  - [Manual Setup — Backend](#manual-setup--backend)
  - [Manual Setup — Frontend](#manual-setup--frontend)
  - [Environment Variables](#environment-variables)
- [Registering a New User](#registering-a-new-user)
  - [Option A — Through the web app](#option-a--through-the-web-app)
  - [Option B — Through the API](#option-b--through-the-api)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [License / Academic Use](#license--academic-use)

---

## Overview

Traditional Learning Management Systems (Moodle, etc.) organize content but don't tutor
interactively. General AI chat tools (ChatGPT) explain concepts on demand but don't follow a
structured curriculum or track progress. This project combines both: a learner works through an
ordered set of IT modules, and an AI tutor answers questions grounded in the content of the
module currently being studied, using Retrieval-Augmented Generation (RAG) instead of the
model's general knowledge.

The system is also genuinely *adaptive*, not just a progress tracker with a chatbot attached: a
learner can take a **diagnostic assessment** before starting a track (or a single module), and the
system uses the resulting per-topic mastery scores to recommend where they should actually start —
skipping topics they've already demonstrated they know instead of forcing everyone through Lesson 1.
See [Diagnostic Assessment & Adaptive Path](#diagnostic-assessment--adaptive-path) below, and the
full design rationale in [`specs/001-diagnostic-assessment/`](specs/001-diagnostic-assessment/).

## Tech Stack

| Layer          | Technology                                                             |
| -------------- | ----------------------------------------------------------------------|
| Backend        | Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/)                |
| Frontend       | [Angular 22](https://angular.dev/)                                     |
| AI / LLM       | Google Gemini (`gemini-flash-latest`) via Google AI Studio             |
| RAG Framework  | [LangChain](https://www.langchain.com/)                               |
| Vector Store   | [ChromaDB](https://www.trychroma.com/) (persisted to `backend/chroma_db`) |
| Relational DB  | SQLite via SQLAlchemy (`backend/sql_app.db`)                          |
| Auth           | Password hashing with `passlib`/`bcrypt`, JWT via `python-jose`        |

## Architecture

```
┌──────────────┐      HTTP/JSON       ┌──────────────────┐
│   Angular    │ ───────────────────▶ │     FastAPI       │
│  Frontend    │ ◀─────────────────── │     Backend        │
│ (port 4200)  │                      │   (port 8000)      │
└──────────────┘                      └─────────┬──────────┘
                                                 │
                     ┌───────────────────────────┼───────────────────────────┐
                     ▼                           ▼                           ▼
              ┌─────────────┐            ┌──────────────┐            ┌──────────────┐
              │   SQLite     │            │   ChromaDB    │            │  Google       │
              │ (users,      │            │ (vector store │            │  Gemini API   │
              │  modules,    │            │  of module/   │            │  (embeddings  │
              │  progress,   │            │  lesson text) │            │  + chat LLM)  │
              │  chat log)   │            └──────────────┘            └──────────────┘
              └─────────────┘
```

Request flow for a chat message: **Angular chat panel → `POST /api/chat` (JWT-protected) → FastAPI
→ ChromaDB retriever (top-3 chunks, optionally filtered to the active module) → relevance-score
gate (redirects clearly off-topic questions back to the module instead of answering them) → Gemini
LLM with retrieved context and a custom tutor prompt → answer + source chunks returned to the
user, and both messages are logged to `chat_messages`.** Full parameter-level detail (chunk size,
embedding model, similarity method, prompt) is in [RAG Pipeline](#rag-pipeline) below.

## Features

### Implemented

- **User registration & login** — `POST /api/auth/register`, `POST /api/auth/login`. Passwords
  are hashed with bcrypt; sessions are stateless JWTs (24h expiry).
- **Authenticated "who am I" endpoint** — `GET /api/auth/me` (also returns `created_at`, used by
  the profile page's "member since").
- **Structured learning content** — Modules and ordered lessons stored relationally
  (`Track → Module → Lesson`). A "Programming" track containing a "Python Programming" module
  (11 lessons) and a "Data Structures" module (10 lessons, Big-O through graphs) is auto-seeded
  on backend startup.
- **AI tutor chat (RAG)**, module-scoped — `POST /api/chat` (JWT-protected) retrieves the most
  relevant chunks for a learner's question from ChromaDB, restricted to the module currently open
  when one is given, and asks Gemini to answer grounded in that retrieved context. A relevance
  floor detects clearly off-topic questions and redirects the learner back to the active module
  instead of letting the LLM answer from outside it. See [RAG Pipeline](#rag-pipeline) for the
  full stage-by-stage breakdown (chunking, embedding model, retrieval, vector store, generation).
- **Chat history persistence** — every question/answer pair is written to `chat_messages`;
  `GET /api/chat/history` (per-module summaries) and `GET /api/chat/history/{module_id}` (full
  transcript) let the frontend restore past conversations.
- **Diagnostic assessment & adaptive starting point** — a learner can take a short diagnostic
  (track-wide or module-scoped) before studying; the system scores each topic, classifies it as
  Mastered / Partially Mastered / Needs Learning, auto-completes mastered lessons, and recommends
  the first lesson that isn't already mastered instead of always starting at Lesson 1. Full design
  and threshold justification in [`specs/001-diagnostic-assessment/`](specs/001-diagnostic-assessment/);
  summary in [Diagnostic Assessment & Adaptive Path](#diagnostic-assessment--adaptive-path).
- **Student profile page** (`/profile`) — account info, overall/per-module progress stats, and a
  breakdown of diagnostic mastery per topic, with a link to (re)take the diagnostic.
- **Global header & footer** — persistent across every route (Lusail University branding/logo,
  nav, logged-in username, logout), instead of each page owning its own chrome.
- **Module & lesson browsing UI** — sidebar lesson list, markdown-rendered lesson content,
  resizable AI tutor chat panel alongside the lesson, and a badge on lessons that were
  auto-completed by the diagnostic (still fully clickable/re-toggleable).
- **Track map UI** — visual list of modules with locked/active/completed states, reflecting real
  per-account progress from `GET /api/progress`, plus a dismissible banner offering the
  diagnostic when the learner hasn't taken one yet.
- **Graceful degradation without an API key** — if `GOOGLE_API_KEY` is not set, the backend
  still starts; only chat/indexing calls fail with a clear error instead of crashing the server.
- **Cross-platform setup scripts** — `setup_and_run.ps1` (Windows) and `setup_and_run.sh`
  (Linux/macOS) that install dependencies, bootstrap `.env`, and launch both servers.
- **Route protection & session expiry handling** — `/dashboard`, `/dashboard/module/:title`,
  `/dashboard/diagnostic`, and `/profile` are guarded by `authGuard`; visiting them without a
  valid session token redirects to `/login` (and returns you to the original page after signing
  in). An `HttpInterceptor` also catches a 401 from an expired/invalid token on any authenticated
  request and force-logs-out + redirects to login, rather than leaving the page in a broken state.
- **Server-side progress tracking (FR-07/08/09)** — lesson completion is tracked per user in the
  database (`LessonProgress`), not the browser. Opening a module records it as the learner's most
  recently accessed module (`UserProgress`, used for resume), and a module's status automatically
  becomes `completed` once all of its lessons are checked off. See
  [API Reference](#api-reference) for the endpoints, and
  [Registering a New User](#registering-a-new-user) for a full curl walkthrough including
  progress calls.
- **Automatic JWT attachment** — an `HttpInterceptor` (`AuthInterceptor`) adds the
  `Authorization: Bearer <token>` header to every outgoing API request once a user is logged in,
  so the frontend can call the authenticated progress endpoints without manual wiring per call.

### Planned / Not Yet Implemented

- **Authorization on `/api/modules/*`** — these content endpoints are still open to
  unauthenticated requests (`/api/chat`, `/api/chat/history*`, `/api/progress/*`, `/api/auth/me`,
  and all diagnostic endpoints already require a valid JWT via `get_current_user`).
- **RAGAS-based accuracy evaluation** of AI tutor answers (planned per the project report,
  Section 9.4).
- **Configurable mastery thresholds** — the 80/60 diagnostic cutoffs are a constant in
  `diagnostic_service.py`, not a per-track admin setting (see
  [research.md §5](specs/001-diagnostic-assessment/research.md) for why that's deliberate for now).
- **A real DB migration tool (Alembic)** — schema changes currently rely on `create_all` plus a
  hand-written `ALTER TABLE` guard for the one column that needed one; fine at this scale, not
  going to stay fine indefinitely.

## RAG Pipeline

The AI tutor is a Retrieval-Augmented Generation pipeline built on LangChain + ChromaDB + Gemini,
implemented in [`backend/app/services/rag_service.py`](backend/app/services/rag_service.py).
Concretely, for each of the five stages:

| Stage | Implementation | Why |
|---|---|---|
| **Document Processing** | Every `Module` and `Lesson`'s markdown content is ingested as a LangChain `Document` and split with `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)` (`ingest_text`, lines 70-86). | 1000 characters keeps a chunk to roughly one lesson subsection (a heading + its explanation/code block) — small enough for the retriever to be precise about *which* part of a lesson is relevant, large enough that a chunk isn't just a code fence with no surrounding explanation. A 100-character overlap (10%) avoids splitting a sentence or a short code example exactly at a chunk boundary, which would otherwise silently drop context right where two chunks meet. |
| **Embedding** | `GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")` (line 54), created lazily on first use so the app can start without a key. | Reuses the same Google AI Studio account/key already needed for the chat LLM — no second provider, no separate billing/auth to manage for a course-scale project. Gemini's embedding model is also dimensionally compatible with the same account's quota/rate limits the chat calls already run under. |
| **Retrieval** | `Chroma.as_retriever(search_kwargs={"k": 3, "filter": {"module_id": ...}})` (`get_retriever`, lines 88-98); similarity is Chroma's default (cosine distance over the embedding vectors). When a `module_id` is given, `query_rag` additionally runs `similarity_search_with_relevance_scores` and compares the best score against `MODULE_SCOPE_RELEVANCE_THRESHOLD = 0.45` (line 32) — below that floor, the question is treated as off-topic for the module and the learner is redirected back to it instead of getting an answer synthesized from irrelevant chunks. | `k=3` is the smallest number that reliably gives the "stuff" combiner (below) enough surrounding context to answer without diluting the prompt with marginally-relevant chunks. The 0.45 floor was calibrated empirically against this project's own content: real on-topic questions score ~0.5-0.6, off-topic ones ~0.3-0.4 (see the comment at lines 119-123). |
| **Vector Storage** | ChromaDB, persisted to `backend/chroma_db/` (`persist_directory=self.persist_dir`, lines 81-84, 90-94). Metadata (`type`, `id`, `title`, `module_id`) is stored alongside each chunk's embedding so retrieval can filter by module without a second lookup. | Chroma needs no separate server process (unlike e.g. Milvus/Weaviate/pgvector-on-a-managed-Postgres) — it's an embedded, file-backed store, which matches this project's single-server academic deployment and keeps the whole RAG stack to one `pip install`. |
| **Generation** | `ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0.7)` (line 62), driven through `RetrievalQA.from_chain_type(chain_type="stuff", chain_type_kwargs={"prompt": TUTOR_PROMPT}, return_source_documents=True)` (lines 139-145). `TUTOR_PROMPT` (lines 10-25) instructs the model to answer from the given course material, cite/stay consistent with it, but also allows it to generate *new* practice exercises in the same topic/difficulty when asked — it isn't restricted to verbatim retrieval for that one case. `return_source_documents=True` is what lets `/api/chat` return the source chunks (grounding/citation) alongside the answer. | `"stuff"` (concatenate all retrieved chunks into one prompt) is the right chain type at `k=3`/1000-char chunks — the combined context comfortably fits in a single call, so there's no need for `map_reduce`/`refine`'s extra LLM round-trips. `gemini-flash-latest` was chosen for chat latency (NFR 2.1.1 targets ≤5s including retrieval) over a heavier Gemini Pro model. |

Everything above is instantiated lazily (`self._embeddings`, `self._llm`, `self.vector_db` all
start `None`) specifically so the backend can boot and serve every non-AI feature — modules,
progress, the diagnostic assessment — even with no `GOOGLE_API_KEY` set at all.

## Diagnostic Assessment & Adaptive Path

Before a learner starts a track (or, separately, before entering a specific module for the first
time), they can take a short diagnostic instead of always beginning at Lesson 1:

1. **Scoring** — each answered question is graded, and a **Topic Score** is computed per lesson:
   `(points earned on that lesson's questions / points available) × 100`, using only lessons that
   had at least one answered question (`diagnostic_service.score_attempt`).
2. **Classification** — `80-100% → Mastered`, `60-79% → Partially Mastered`, `<60% → Needs
   Learning` (`diagnostic_service.classify`). These aren't arbitrary — see
   [`research.md §1`](specs/001-diagnostic-assessment/research.md) for the mastery-learning-literature
   and risk-asymmetry justification for landing on 80/60 rather than, say, a single 70% pass bar.
3. **Adapting the path** — the recommended starting lesson is the first one (in track/module order)
   that isn't Mastered; a lesson with *no* diagnostic result at all (never answered) is treated as
   not-mastered rather than assumed known (`diagnostic_service.recommend_start`). Mastered lessons
   are auto-marked complete (tagged `completion_source="diagnostic"` so the UI can badge them
   distinctly from manually-studied lessons), but a diagnostic retake can never un-complete a
   lesson the learner already finished, manually or otherwise.

Reused `Lesson` as the topic unit rather than introducing a parallel `Topic` table — see
[`spec.md §2`](specs/001-diagnostic-assessment/spec.md) for why. New endpoints live in
[`backend/app/routers/diagnostics.py`](backend/app/routers/diagnostics.py) (see
[API Reference](#api-reference)); new tables (`diagnostic_questions`, `diagnostic_attempts`,
`diagnostic_answers`, `topic_mastery`) are in [Database Schema](#database-schema).

## Pages & Screens

| Route                          | Component               | Description                                                                 |
| ------------------------------- | ------------------------ | ----------------------------------------------------------------------------- |
| `/login`                        | `LoginComponent`         | Username/password sign-in.                                                   |
| `/register`                     | `RegisterComponent`      | Create a new account, then auto-signs in.                                    |
| `/dashboard`                    | `DashboardComponent`     | Landing page after login; shows the track map and the AI tutor chat side by side. |
| `/dashboard/diagnostic`         | `DiagnosticAssessmentComponent` | Take (or retake) the diagnostic: intro → questions grouped by topic → scored results with a recommended starting lesson. |
| `/dashboard/module/:title`      | `ModuleViewComponent`    | Full lesson reader: sidebar lesson list (badged where a lesson was auto-completed via diagnostic), markdown lesson content, per-lesson completion toggle, and a resizable AI tutor chat panel. |
| `/profile`                      | `ProfileComponent`       | Account info, overall/per-module progress stats, and diagnostic mastery breakdown per topic. |
| (embedded) Track Map            | `TrackMapComponent`      | Visual list of modules with locked/active/completed status; clicking a module opens it; shows a diagnostic prompt banner. |
| (embedded) AI Tutor Chat        | `ChatInterfaceComponent` | Chat UI that posts questions to `/api/chat` and renders markdown answers.     |
| (global) Header / Footer        | `HeaderComponent` / `FooterComponent` | Persistent across every route: logo, nav, logged-in username, logout, and site footer. |

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, module/lesson/progress/chat routes, startup seeding
│   │   ├── core/security.py     # Password hashing, JWT issuing/validation
│   │   ├── db/database.py       # SQLAlchemy engine/session
│   │   ├── models/models.py     # User, Track, Module, Lesson, UserProgress, LessonProgress,
│   │   │                        # ChatMessage, DiagnosticQuestion, DiagnosticAttempt,
│   │   │                        # DiagnosticAnswer, TopicMastery
│   │   ├── schemas/schemas.py   # Pydantic request/response models
│   │   ├── routers/diagnostics.py   # Diagnostic assessment endpoints (APIRouter)
│   │   └── services/
│   │       ├── rag_service.py           # LangChain + ChromaDB + Gemini RAG pipeline
│   │       └── diagnostic_service.py    # Scoring/classification/recommendation logic
│   ├── tests/test_diagnostic_service.py # Unit tests (classify/recommend_start boundaries)
│   ├── requirements.txt
│   ├── .env                     # GOOGLE_API_KEY, JWT_SECRET_KEY (not committed)
│   ├── sql_app.db                # SQLite database (created on first run)
│   └── chroma_db/                # Vector store (created on first run)
├── frontend/
│   ├── src/img/lu-logo.webp     # Lusail University logo (served as /img/lu-logo.webp)
│   └── src/app/
│       ├── core/                # auth.service.ts, auth.guard.ts, auth.interceptor.ts,
│       │                        # module.service.ts, progress.service.ts, diagnostic.service.ts
│       ├── shared/              # header/, footer/ — global chrome wrapped around every route
│       └── features/
│           ├── auth/            # login, register
│           ├── dashboard/
│           ├── track-map/
│           ├── module-view/
│           ├── diagnostic/      # diagnostic-taking UI + results
│           ├── profile/         # student profile / progress-tracking page
│           └── chat/
├── docs/
│   ├── reports/requirements.md
│   └── logbook/
├── specs/001-diagnostic-assessment/  # spec-kit docs: spec.md, research.md, plan.md, tasks.md
├── setup_and_run.ps1             # Windows setup + run script
└── setup_and_run.sh               # Linux/macOS setup + run script
```

## Prerequisites

- **Python** 3.10 or later
- **Node.js `^22.22.3` / `^24.15.0` / `>=26.0.0`** + npm — required by Angular 22. Older Node
  versions (including Node 18/20) will **not** run `npm install` (blocked deliberately via
  `engine-strict` in `frontend/.npmrc`, so the failure is immediate and clear instead of a
  confusing error mid-build). On Windows, check your version with `node -v`; if it's too old,
  either install/upgrade via winget (`winget install -e --id OpenJS.NodeJS.LTS`) or use
  [nvm-windows](https://github.com/coreybutler/nvm-windows). On Linux/macOS, use
  [nvm](https://github.com/nvm-sh/nvm) if you need to manage multiple Node versions.
- A **Google AI Studio API key** for Gemini — get one free at
  [aistudio.google.com](https://aistudio.google.com/) (only required for the AI tutor chat; the
  rest of the app works without it)

## Setup

### Quick Start (automated scripts)

The setup scripts install all dependencies, create a `venv`, generate `backend/.env` with a
random JWT secret, and start both servers.

**Windows (PowerShell):**

```powershell
.\setup_and_run.ps1
# Optional: .\setup_and_run.ps1 -BackendPort 8000 -FrontendPort 4200
```

**Linux / macOS:**

```bash
chmod +x setup_and_run.sh   # first time only
./setup_and_run.sh
# Optional flags: --backend-port 8000 --frontend-port 4200 --auto-install
```

Both scripts print the backend and frontend URLs once servers are up. Either way, **open
`backend/.env` afterward and set `GOOGLE_API_KEY`** — without it, everything works except the AI
tutor chat.

### Manual Setup — Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# Create backend/.env (see Environment Variables below)

uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- On first run, the server auto-seeds a "Programming" track with a "Python Programming" module
  (11 lessons, plus a diagnostic question bank for its first 5) and a "Data Structures" module
  (10 lessons), and indexes all of it into ChromaDB.

### Manual Setup — Frontend

```bash
cd frontend
npm install
npm start          # equivalent to: ng serve
```

Open `http://localhost:4200`.

### Environment Variables

Create `backend/.env` with:

```env
GOOGLE_API_KEY=your-google-ai-studio-key
JWT_SECRET_KEY=a-long-random-string
```

| Variable          | Required | Purpose                                                            |
| ----------------- | -------- | -------------------------------------------------------------------|
| `GOOGLE_API_KEY`  | For chat | Gemini API key used for embeddings and chat completions.           |
| `JWT_SECRET_KEY`  | Recommended | Signing key for login tokens. If omitted, an insecure development default is used — always set this for anything beyond local testing. |

The setup scripts generate `JWT_SECRET_KEY` for you automatically; you only need to fill in
`GOOGLE_API_KEY` by hand.

### Troubleshooting (Windows)

- **`npm warn deprecated ...` lines during setup are expected**, not a failure — they're upstream
  Angular/tooling deprecation notices printed to stderr. `setup_and_run.ps1` runs native
  commands (pip, npm, winget) with output visible and checks their real exit code afterward,
  rather than treating any stderr line as fatal (a stock Windows PowerShell 5.1 gotcha: with
  `$ErrorActionPreference = "Stop"`, a native command's stderr output can abort the script even
  when the command itself succeeds).
- **First-time npm install on Windows may need `npm approve-scripts`** if you see a
  `npm warn allow-scripts` notice — recent npm versions (10+) block a package's install/postinstall
  scripts (e.g. `esbuild`'s, which fetches its native binary) until approved. This repo's
  `frontend/package.json` already commits the approved list (`allowScripts`), so a normal
  `npm ci`/`npm install` should not prompt for this; if it does, run
  `npm approve-scripts --allow-scripts-pending` inside `frontend/`.
- If `setup_and_run.ps1` fails at "Creating backend/.env..." with a `RandomNumberGenerator`/`Fill`
  error, you're on an older copy of the script — it originally used a .NET Core–only API that
  doesn't exist on Windows PowerShell 5.1's .NET Framework runtime. Pull the latest script (it now
  uses `RNGCryptoServiceProvider`, which works on both).
- **"Port 8000/4200 is already in use" / `ng serve`'s "Would you like to use a different port?"
  prompt**: this happens if a backend/frontend from a previous run is still alive (or, on Windows,
  if `uvicorn --reload`'s watcher process was killed but its actual server child was left orphaned
  and still holding the port). `setup_and_run.ps1` now checks both ports before starting and stops
  whatever it finds there (walking the full parent/child process tree, not just the top-level
  PID), so a normal re-run of the script clears this automatically. If you're running the servers
  manually (`npm start` / `uvicorn` directly, not via the script) and hit this, find and stop the
  process yourself first, e.g. `Get-NetTCPConnection -LocalPort 4200 -State Listen | Select
  OwningProcess` then `Stop-Process -Id <pid> -Force`.

## Registering a New User

### Option A — Through the web app

1. Start both servers (see [Setup](#setup)).
2. Open `http://localhost:4200/register`.
3. Fill in a **username**, **email**, and **password**, then submit.
4. On success you are logged in automatically and redirected to `/dashboard`.

(From the login page at `/login`, there's also a **"Need an account? Register"** link.)

### Option B — Through the API

Useful for testing or scripting. With the backend running on `localhost:8000`:

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "ali", "email": "ali@example.com", "password": "a-strong-password"}'

# 2. Log in to get a JWT
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ali", "password": "a-strong-password"}'
# -> {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Call an authenticated endpoint
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <paste access_token here>"
```

You can also do all of this interactively via the Swagger UI at
`http://localhost:8000/docs` — expand `POST /api/auth/register` and `POST /api/auth/login`, use
"Try it out", then click the padlock icon to authorize subsequent requests with the returned
token.

### Trying progress tracking via the API

Continuing from the token obtained above:

```bash
TOKEN="<paste access_token here>"

# Look up the seeded "Python Programming" module to get real module/lesson IDs
# (it's seeded first, so on a fresh database it's module_id=1; check the response
# to be sure rather than assuming, especially if you've reseeded before)
curl -s "http://localhost:8000/api/modules/title/Python%20Programming" | python3 -m json.tool

# Record that the learner opened module 1 (creates/updates their progress row)
curl -X POST http://localhost:8000/api/progress/modules/1/open \
  -H "Authorization: Bearer $TOKEN"

# Mark lesson 1 as complete
curl -X PUT http://localhost:8000/api/progress/lessons/1 \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"completed": true}'

# See overall progress for this module
curl http://localhost:8000/api/progress/modules/1 -H "Authorization: Bearer $TOKEN"

# See which module to resume on next login
curl http://localhost:8000/api/progress/resume -H "Authorization: Bearer $TOKEN"
```

### Trying the diagnostic assessment via the API

```bash
TOKEN="<paste access_token here>"
TRACK_ID=1   # the seeded "Programming" track; check GET /api/modules if unsure

# Has this user already taken the diagnostic? (null on a fresh account)
curl -s "http://localhost:8000/api/tracks/$TRACK_ID/diagnostic/status" -H "Authorization: Bearer $TOKEN"

# Start it — returns an attempt_id and the question bank, grouped by topic
curl -s -X POST "http://localhost:8000/api/tracks/$TRACK_ID/diagnostic/start" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Submit answers (replace attempt_id/question_id/selected_choices with real values
# from the response above)
curl -s -X POST "http://localhost:8000/api/diagnostic/attempts/1/submit" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"answers": [{"question_id": 1, "selected_choices": [1]}]}' | python3 -m json.tool
# -> per-topic scores/bands, auto-completed lesson IDs, and a recommended starting lesson

# Full per-topic mastery breakdown (what the profile page shows)
curl -s "http://localhost:8000/api/tracks/$TRACK_ID/mastery" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

## API Reference

| Method | Path                                    | Auth required | Description                                            |
| ------ | ---------------------------------------- | -------------- | -------------------------------------------------------|
| POST   | `/api/auth/register`                    | No             | Create a new user account.                             |
| POST   | `/api/auth/login`                        | No             | Exchange username/password for a JWT.                  |
| GET    | `/api/auth/me`                           | Yes (Bearer)   | Return the currently authenticated user (including `created_at`). |
| GET    | `/api/modules`                          | No             | List all modules (with their lessons), ordered.         |
| GET    | `/api/modules/{module_id}`              | No             | Fetch a module (with its lessons) by numeric ID.        |
| GET    | `/api/modules/title/{title}`            | No             | Fetch a module (with its lessons) by title.             |
| POST   | `/api/chat`                              | Yes (Bearer)   | Ask the AI tutor a question; returns a RAG-grounded answer and source chunks, module-scoped when a module/lesson context is given. Logs both messages to `chat_messages`. |
| GET    | `/api/chat/history`                      | Yes (Bearer)   | One entry per module the learner has chatted in, most recent first. |
| GET    | `/api/chat/history/{module_id}`         | Yes (Bearer)   | Full chat transcript for one module.                    |
| POST   | `/api/progress/modules/{module_id}/open`| Yes (Bearer)   | Mark a module as opened/in-progress and update `last_accessed` (used for resume). |
| GET    | `/api/progress/modules/{module_id}`     | Yes (Bearer)   | Get the current user's status, completion %, completed lesson IDs, and which of those were diagnostic-auto-completed, for one module. |
| PUT    | `/api/progress/lessons/{lesson_id}`     | Yes (Bearer)   | Mark a lesson complete/incomplete (`{"completed": true\|false}`); recomputes the parent module's status. |
| GET    | `/api/progress`                          | Yes (Bearer)   | List progress for every module the current user has touched. |
| GET    | `/api/progress/resume`                   | Yes (Bearer)   | The module the current user most recently accessed (or `null`). |
| GET    | `/api/tracks/{track_id}/diagnostic/status` | Yes (Bearer) | Has the current user already taken this track's diagnostic? |
| POST   | `/api/tracks/{track_id}/diagnostic/start`  | Yes (Bearer) | Start a track-wide diagnostic attempt; returns questions grouped by topic. |
| POST   | `/api/modules/{module_id}/diagnostic/start`| Yes (Bearer) | Start a module-scoped diagnostic attempt. |
| POST   | `/api/diagnostic/attempts/{attempt_id}/submit` | Yes (Bearer) | Submit answers; scores each topic, auto-completes mastered lessons, and returns the recommended starting lesson. |
| GET    | `/api/tracks/{track_id}/mastery`        | Yes (Bearer)   | Full per-topic mastery breakdown for the current user (used by the profile page). |
| GET    | `/api/tracks/{track_id}/recommendation` | Yes (Bearer)   | Recompute the recommended starting lesson without taking a new diagnostic. |

Full interactive documentation is always available at `/docs` while the backend is running.

## Database Schema

| Table             | Purpose                                                                 |
| ------------------ | ------------------------------------------------------------------------|
| `users`            | Account credentials (`hashed_password`, never plaintext).              |
| `tracks`           | Top-level learning tracks (e.g., "Programming").                       |
| `modules`          | Ordered modules within a track; carries an AI-tutor `policy` string.   |
| `lessons`          | Ordered lesson content within a module (markdown) — also the "topic" unit for diagnostics. |
| `user_progress`    | Per-user, per-module status (`in_progress` / `completed`) and `last_accessed`, used for resume. |
| `lesson_progress`  | Per-user, per-lesson completion checkbox (`completed`, `completed_at`, `completion_source`: `"manual"` or `"diagnostic"`); a module's overall status is derived from these. |
| `chat_messages`    | Per-user, per-module chat log; written on every `/api/chat` call.      |
| `diagnostic_questions` | Question bank per lesson/topic (prompt, choices, correct answer(s), points). |
| `diagnostic_attempts`  | One per diagnostic-taking event (`track_id`, optional `module_id` for a module-scoped attempt, `submitted_at`). |
| `diagnostic_answers`   | One per (attempt, question); what was selected and points earned.      |
| `topic_mastery`        | Current derived state per (user, lesson): score, band, source attempt — the read model recommendations and progress-skip logic query. |

See [`specs/001-diagnostic-assessment/plan.md`](specs/001-diagnostic-assessment/plan.md) for the
full column-level schema and migration approach for the four diagnostic tables.

## Known Limitations

This is an academic proof-of-concept, not a production system:

- The Angular route guard only checks that a token *exists* in `localStorage`, not that it is
  still valid/unexpired before navigating — an expired token still lets the page load, though the
  `AuthInterceptor` now catches the resulting 401 on the first API call and redirects to `/login`
  automatically, so the learner isn't left looking at a silently broken page.
- The backend content endpoints (`/api/modules/*`) are not yet protected by `get_current_user` —
  the frontend guard stops navigation, but the endpoints would still respond to an
  unauthenticated direct request. (`/api/chat`, `/api/progress/*`, `/api/auth/me`, and every
  diagnostic endpoint *are* protected.)
- Only one track ("Programming", containing the "Python Programming" and "Data Structures"
  modules) is seeded; no cybersecurity/networking/data-science tracks yet.
- Diagnostic questions are only authored for the first 5 lessons of "Python Programming" — the
  rest of that module and all of "Data Structures" have no question bank yet, so a diagnostic
  covering them would 404 (by design — see spec.md's "insufficient data" edge case).
- No DB migration tool (Alembic); schema changes rely on `create_all` plus a hand-written
  `ALTER TABLE` guard for `lesson_progress.completion_source` specifically.
- Single-server deployment only; no containerization or cloud deployment configuration.

## Roadmap

1. Expand beyond the two seeded modules — author diagnostic question banks for the remaining
   Python Programming lessons and all of Data Structures, and add further tracks (cybersecurity,
   networking, data science).
2. Protect `/api/modules/*` with `get_current_user`.
3. Implement the RAGAS-based AI accuracy evaluation described in the project report.
4. Introduce Alembic (or similar) once schema changes become frequent enough that the
   `ALTER TABLE` guard pattern stops scaling.
5. Consider per-track-configurable mastery thresholds if real usage data suggests 80/60 isn't
   right for every subject area (see `research.md §5`).
6. Migrate off the deprecated Webpack-based Angular builder to `@angular/build` (esbuild/Vite) —
   `ng update @angular/cli --name use-application-builder`. Purely a build-tooling change with no
   functional impact; deferred here to keep this upgrade's diff reviewable.

## License / Academic Use

This project is developed as part of the ITCC 403 Graduation Project at Lusail University's
College of Information Technology. Intended for academic evaluation.
