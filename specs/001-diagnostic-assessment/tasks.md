# Tasks: Diagnostic Assessment & Adaptive Starting Point

Derived from [plan.md](./plan.md). Ordered by dependency; `[P]` = safe to parallelize with other `[P]` tasks in the same group since they touch disjoint files.

**Status: implemented (2026-09-17).** All tasks below are done and verified — see the "Verification performed" note at the end for how, since no CI is wired up yet in this repo.

## Group 1 — Schema

- [x] **T1.** Add `DiagnosticQuestion`, `DiagnosticAttempt`, `DiagnosticAnswer`, `TopicMastery`, `MasteryBand` to [backend/app/models/models.py](../../backend/app/models/models.py) per plan.md §2.1.
- [x] **T2.** Add `completion_source` column to `LessonProgress` in the same file (plan.md §2.2).
- [x] **T3.** Add the startup `PRAGMA table_info` guard in `main.py`'s startup path to `ALTER TABLE lesson_progress ADD COLUMN completion_source TEXT` when missing (plan.md §2.3).

## Group 2 — Scoring Service

- [x] **T4.** Create [backend/app/services/diagnostic_service.py](../../backend/app/services/diagnostic_service.py) with `classify()`, `score_attempt()`, `recommend_start()`, `apply_mastery_to_progress()`, `grade_answer()` (plan.md §3.3).
- [x] **T5.** Unit tests for `classify()` boundaries (79/80, 59/60) and `recommend_start()` (empty/all-mastered/none-mastered/mixed/missing-data) — [backend/tests/test_diagnostic_service.py](../../backend/tests/test_diagnostic_service.py). `pytest` added to [requirements.txt](../../backend/requirements.txt) (resolves open question #1 below).
- [x] **T6.** FR-D10 regression guard (manually-completed lesson survives a lower-scoring diagnostic retake) — verified via an end-to-end scripted run against the live API (see Verification note); not yet captured as a committed `pytest` integration test because `app.main` imports `rag_service`, which hard-imports `langchain`/`chromadb` at module load time — a real test run needs those installed (or `rag_service`'s import made lazy, which is a separate, pre-existing architectural change outside this feature's scope). Flagged as a follow-up.

## Group 3 — Schemas & Endpoints

- [x] **T7.** Add `DiagnosticQuestionOut`, `DiagnosticStartOut`, `DiagnosticAnswerIn`, `DiagnosticSubmitIn`, `TopicMasteryOut`, `DiagnosticResultOut`, `DiagnosticStatusOut`, `RecommendationOut` to [backend/app/schemas/schemas.py](../../backend/app/schemas/schemas.py) (plan.md §3.1). `ModuleProgressOut` also gained `diagnostic_completed_lesson_ids` for FR-D12.
- [x] **T8.** Implement `GET /api/tracks/{track_id}/diagnostic/status`.
- [x] **T9.** Implement `POST /api/tracks/{track_id}/diagnostic/start` and `POST /api/modules/{module_id}/diagnostic/start`.
- [x] **T10.** Implement `POST /api/diagnostic/attempts/{attempt_id}/submit` (wires into `diagnostic_service`).
- [x] **T11.** Implement `GET /api/tracks/{track_id}/recommendation`.
- [x] **T12.** Extracted into [backend/app/routers/diagnostics.py](../../backend/app/routers/diagnostics.py) (an `APIRouter` included from `main.py` with prefix `/api`), per the plan's recommendation — `main.py` was already ~490 lines.
- [x] **T20.** (Added post-launch, for the student profile page) Implement `GET /api/tracks/{track_id}/mastery` — full per-topic mastery breakdown for the current user; and add `created_at` to `UserOut`/`GET /api/auth/me`.

## Group 4 — Content

- [x] **T13.** Authored a diagnostic question bank (3 questions each, single-choice) for the first 5 "Python Programming" lessons — Introduction to Python, Variables and Data Types, Operators and Expressions, Control Flow: Conditionals and Loops, Functions — in [backend/app/seed_data.py](../../backend/app/seed_data.py) (`DIAGNOSTIC_QUESTIONS`), seeded idempotently by lesson title via `_seed_diagnostic_questions()` in `main.py`.

## Group 5 — Frontend (Angular)

- [x] **T14.** Diagnostic banner on the track map (dismissible, explicit "Take the diagnostic" / "Dismiss" per FR-D11) — [track-map.component.ts/html/scss](../../frontend/src/app/features/track-map/).
- [x] **T15.** Diagnostic-taking view — [diagnostic-assessment.component.ts/html/scss](../../frontend/src/app/features/diagnostic/), routed at `/dashboard/diagnostic`.
- [x] **T16.** Diagnostic result summary screen (per-topic bands + recommended start lesson) — same component, `result` state.
- [x] **T17.** Module view now badges lessons with `completion_source="diagnostic"` as "auto" (tooltip explains why), distinct from manually completed ones, still fully clickable (FR-D12) — [module-view.component.ts/html/scss](../../frontend/src/app/features/module-view/).
- [x] **T21.** (Added post-launch) Student profile page (`/profile`, `ProfileComponent`) — account info, overall/per-module progress, and a diagnostic mastery breakdown with mastered/partial/needs-learning chips, consuming T20's `/mastery` endpoint.
- [x] **T22.** (Added post-launch) Global header/footer (`shared/header`, `shared/footer`) wrapping every route, replacing each page's own ad hoc chrome; converted full-bleed pages (`dashboard`, `module-view`, `not-found`, `error-page`) from `100vh`/`100vw` to `height:100%`/`width:100%` so they fill the space under the new header/footer correctly.

## Group 6 — Validation

- [x] **T18.** Manual end-to-end run performed via a scripted `TestClient` session (register → list modules → diagnostic status is null → start track diagnostic → answer Intro/Variables correctly and Functions incorrectly, leave others unanswered → submit): confirmed Intro/Variables → `mastered` (auto-completed), Functions → `needs_learning`, Operators/Loops left unscored (unanswered), and recommended start correctly resolved to "Operators and Expressions" (first non-mastered lesson in order). Also verified the module-scoped `start` endpoint and the standalone `recommendation` endpoint.
- [x] **T19.** Confirmed via the same run that `GET /api/progress` / `/api/progress/modules/{id}` / `PUT /api/progress/lessons/{id}` behavior is unchanged for the non-diagnostic path — the only addition is the new `diagnostic_completed_lesson_ids` field, which is additive and empty unless a diagnostic has been taken. Also separately verified the `completion_source` column migration guard against a hand-built pre-existing `lesson_progress` table (no such column), confirming the `ALTER TABLE` runs once and legacy rows are preserved untouched.
- [x] **T23.** (Added post-launch) End-to-end headless-browser verification of the header/footer/profile rollout: registered a real test account, drove it through headless Chrome across login, 404, dashboard, module-view, diagnostic, and profile pages; confirmed no viewport overflow and that the profile's mastery breakdown reflects live diagnostic data. Caught and fixed a real layout bug in the process (the "auto" diagnostic badge was crushing lesson titles in the sidebar due to a missing `min-width:0`/`white-space:nowrap`).

## Open Questions — resolved during implementation

1. **Test framework:** introduced `pytest` (added to `requirements.txt`), with `backend/tests/test_diagnostic_service.py` covering the dependency-free scoring/recommendation logic. A full API-level integration suite is still blocked on `rag_service`'s hard `langchain`/`chromadb` import at module load time (pre-existing, unrelated to this feature) — recommend making that import lazy in a follow-up so `TestClient`-based tests don't need the full RAG dependency stack installed.
2. **Module-scoped diagnostic mandatoriness:** kept skippable/optional, matching the track-level diagnostic (FR-D11). The frontend does not yet surface a module-entry prompt (only the track-level banner is wired up in T14) — module-scoped diagnostics are reachable via the API (`POST /api/modules/{module_id}/diagnostic/start`) but have no dedicated UI trigger yet. Follow-up if product wants that surfaced.
3. **Threshold configurability:** kept as the module-level constant `MASTERY_THRESHOLDS` in `diagnostic_service.py` (research.md §5) — no admin UI exists yet, so a schema-backed config table would be speculative. Revisit if instructors need per-track tuning.

## Verification performed

No CI/test runner was previously wired into this repo, and the dev environment used to implement this feature had no Python packages installed at all. Verification was done by:
- Creating a disposable local virtualenv (`backend/venv/`, gitignored, deleted after) with the packages from `requirements.txt` (minus `langchain`/`chromadb`, stubbed out for the test run only since they're irrelevant to this feature and heavy to install).
- Running a full scripted scenario through FastAPI's `TestClient` against a throwaway SQLite file covering: registration/login, diagnostic status before/after, scoring correctness, auto-completion, the FR-D10 no-revert guard, the recommendation endpoint, and the module-scoped start endpoint — all passed.
- Running `backend/tests/test_diagnostic_service.py` under `pytest` (12 tests, all passing) with only `sqlalchemy` + `pytest` installed, confirming those unit tests have no hidden dependency on the RAG stack.
- Running `npm install && npx ng build` in `frontend/` to confirm the new component, routes, and service compile cleanly under Angular's production build pipeline.
- For the header/footer/profile follow-up: a second disposable venv + a headless-Chrome pass against the real built frontend and a real (stubbed-RAG) backend, screenshotting login/dashboard/module-view/diagnostic/profile/404 to confirm the new shell layout doesn't overflow and that real API data renders correctly end-to-end.
