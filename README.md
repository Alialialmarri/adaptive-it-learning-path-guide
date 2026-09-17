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

Request flow for a chat message: **Angular chat panel → `POST /api/chat` → FastAPI → ChromaDB
retriever (top-k relevant chunks) → Gemini LLM with retrieved context → answer returned to the
user.**

## Features

### Implemented

- **User registration & login** — `POST /api/auth/register`, `POST /api/auth/login`. Passwords
  are hashed with bcrypt; sessions are stateless JWTs (24h expiry).
- **Authenticated "who am I" endpoint** — `GET /api/auth/me`.
- **Structured learning content** — Modules and ordered lessons stored relationally
  (`Track → Module → Lesson`). A full "Data Structures" module (10 lessons, Big-O through
  graphs) is auto-seeded on backend startup.
- **AI tutor chat (RAG)** — `POST /api/chat` embeds module/lesson content into ChromaDB on
  startup, retrieves the most relevant chunks for a learner's question, and asks Gemini to
  answer using that retrieved context rather than open-ended knowledge.
- **Module & lesson browsing UI** — sidebar lesson list, markdown-rendered lesson content,
  resizable AI tutor chat panel alongside the lesson.
- **Track map UI** — visual list of modules with locked/active/completed states.
- **Graceful degradation without an API key** — if `GOOGLE_API_KEY` is not set, the backend
  still starts; only chat/indexing calls fail with a clear error instead of crashing the server.
- **Cross-platform setup scripts** — `setup_and_run.ps1` (Windows) and `setup_and_run.sh`
  (Linux/macOS) that install dependencies, bootstrap `.env`, and launch both servers.
- **Route protection** — `/dashboard` and `/dashboard/module/:title` are guarded by
  `authGuard`; visiting them without a valid session token redirects to `/login` (and returns you
  to the original page after signing in).
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

These map to the functional requirements in the project's interim report but are not wired up
in the current codebase:

- **Chat history persistence** — the `ChatMessage` table exists but `/api/chat` does not write to
  it yet; conversations are not saved.
- **Module-scoped retrieval** — RAG currently searches across *all* indexed content rather than
  filtering by the module the learner has open, so out-of-scope questions are not yet redirected
  back to the active module.
- **Authorization on content endpoints** — `/api/modules/*` and `/api/chat` are still open to
  unauthenticated requests (only the `/api/progress/*` and `/api/auth/me` endpoints currently
  require a valid JWT via `get_current_user`).
- **RAGAS-based accuracy evaluation** of AI tutor answers (planned per the project report,
  Section 9.4).

## Pages & Screens

| Route                          | Component               | Description                                                                 |
| ------------------------------- | ------------------------ | ----------------------------------------------------------------------------- |
| `/login`                        | `LoginComponent`         | Username/password sign-in.                                                   |
| `/register`                     | `RegisterComponent`      | Create a new account, then auto-signs in.                                    |
| `/dashboard`                    | `DashboardComponent`     | Landing page after login; shows the track map and the AI tutor chat side by side. |
| `/dashboard/module/:title`      | `ModuleViewComponent`    | Full lesson reader: sidebar lesson list, markdown lesson content, per-lesson completion toggle, and a resizable AI tutor chat panel. |
| (embedded) Track Map            | `TrackMapComponent`      | Visual list of modules with locked/active/completed status; clicking a module opens it. |
| (embedded) AI Tutor Chat        | `ChatInterfaceComponent` | Chat UI that posts questions to `/api/chat` and renders markdown answers.     |

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, routes, startup seeding
│   │   ├── core/security.py     # Password hashing, JWT issuing/validation
│   │   ├── db/database.py       # SQLAlchemy engine/session
│   │   ├── models/models.py     # User, Track, Module, Lesson, UserProgress, LessonProgress, ChatMessage
│   │   ├── schemas/schemas.py   # Pydantic request/response models
│   │   └── services/rag_service.py  # LangChain + ChromaDB + Gemini RAG pipeline
│   ├── requirements.txt
│   ├── .env                     # GOOGLE_API_KEY, JWT_SECRET_KEY (not committed)
│   ├── sql_app.db                # SQLite database (created on first run)
│   └── chroma_db/                # Vector store (created on first run)
├── frontend/
│   └── src/app/
│       ├── core/                # auth.service.ts, auth.guard.ts, auth.interceptor.ts,
│       │                        # module.service.ts, progress.service.ts
│       └── features/
│           ├── auth/            # login, register
│           ├── dashboard/
│           ├── track-map/
│           ├── module-view/
│           └── chat/
├── docs/
│   ├── reports/requirements.md
│   └── logbook/
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
- On first run, the server auto-seeds a "Data Structures" module with 10 lessons and indexes
  them into ChromaDB.

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

# Look up the seeded module to get real IDs
curl -s "http://localhost:8000/api/modules/title/Data%20Structures" | python3 -m json.tool

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

## API Reference

| Method | Path                                    | Auth required | Description                                            |
| ------ | ---------------------------------------- | -------------- | -------------------------------------------------------|
| POST   | `/api/auth/register`                    | No             | Create a new user account.                             |
| POST   | `/api/auth/login`                        | No             | Exchange username/password for a JWT.                  |
| GET    | `/api/auth/me`                           | Yes (Bearer)   | Return the currently authenticated user.                |
| GET    | `/api/modules/{module_id}`              | No             | Fetch a module (with its lessons) by numeric ID.        |
| GET    | `/api/modules/title/{title}`            | No             | Fetch a module (with its lessons) by title.             |
| POST   | `/api/chat`                              | No             | Ask the AI tutor a question; returns a RAG-grounded answer and source chunks. |
| POST   | `/api/progress/modules/{module_id}/open`| Yes (Bearer)   | Mark a module as opened/in-progress and update `last_accessed` (used for resume). |
| GET    | `/api/progress/modules/{module_id}`     | Yes (Bearer)   | Get the current user's status, completion %, and completed lesson IDs for one module. |
| PUT    | `/api/progress/lessons/{lesson_id}`     | Yes (Bearer)   | Mark a lesson complete/incomplete (`{"completed": true\|false}`); recomputes the parent module's status. |
| GET    | `/api/progress`                          | Yes (Bearer)   | List progress for every module the current user has touched. |
| GET    | `/api/progress/resume`                   | Yes (Bearer)   | The module the current user most recently accessed (or `null`). |

Full interactive documentation is always available at `/docs` while the backend is running.

## Database Schema

| Table             | Purpose                                                                 |
| ------------------ | ------------------------------------------------------------------------|
| `users`            | Account credentials (`hashed_password`, never plaintext).              |
| `tracks`           | Top-level learning tracks (e.g., "Programming").                       |
| `modules`          | Ordered modules within a track; carries an AI-tutor `policy` string.   |
| `lessons`          | Ordered lesson content within a module (markdown).                     |
| `user_progress`    | Per-user, per-module status (`in_progress` / `completed`) and `last_accessed`, used for resume. |
| `lesson_progress`  | Per-user, per-lesson completion checkbox (`completed`, `completed_at`); a module's overall status is derived from these. |
| `chat_messages`    | Per-user, per-module chat log. *Model exists; not yet written to.*     |

## Known Limitations

This is an academic proof-of-concept, not a production system:

- The Angular route guard only checks that a token *exists* in `localStorage`, not that it is
  still valid/unexpired — an expired token lets the page load but subsequent API calls will 401.
- The backend content endpoints (`/api/modules/*`, `/api/chat`) are not yet protected by
  `get_current_user` — the frontend guard stops navigation, but the endpoints would still respond
  to an unauthenticated direct request. (`/api/progress/*` and `/api/auth/me` *are* protected.)
- The dashboard's track map does not yet call `GET /api/progress` to reflect real completion —
  it still shows mock/hardcoded status for tracks other than the currently viewable module.
- RAG retrieval is global, not filtered to the currently open module.
- Only one learning track ("Data Structures") is seeded.
- Single-server deployment only; no containerization or cloud deployment configuration.

## Roadmap

1. Have the track map / dashboard call `GET /api/progress` so module status reflects real,
   per-account completion instead of mock data.
2. Persist chat messages per user/module.
3. Filter RAG retrieval by the active module's document metadata.
4. Protect `/api/modules/*` and `/api/chat` with `get_current_user`.
5. Expand beyond the single "Data Structures" track (cybersecurity, networking, data science).
6. Implement the RAGAS-based AI accuracy evaluation described in the project report.
7. Migrate off the deprecated Webpack-based Angular builder to `@angular/build` (esbuild/Vite) —
   `ng update @angular/cli --name use-application-builder`. Purely a build-tooling change with no
   functional impact; deferred here to keep this upgrade's diff reviewable.

## License / Academic Use

This project is developed as part of the ITCC 403 Graduation Project at Lusail University's
College of Information Technology. Intended for academic evaluation.
