# Implementation Plan: Diagnostic Assessment & Adaptive Starting Point

**Input:** [spec.md](./spec.md) · **Thresholds justification:** [research.md](./research.md)

## 1. Current System Snapshot (as-built, for grounding the plan)

This section answers the "clarify the actual techniques/technologies used" part of the request, so the diagnostic feature can be positioned correctly against what already exists rather than assumed.

| Layer | Technology | Where |
|---|---|---|
| Backend framework | FastAPI (Python) | [backend/app/main.py](../../backend/app/main.py) |
| ORM | SQLAlchemy (declarative models) | [backend/app/models/models.py](../../backend/app/models/models.py) |
| Database | SQLite (file `sql_app.db`), via `sqlite:///./sql_app.db` | [backend/app/db/database.py](../../backend/app/db/database.py) |
| Auth | Self-issued JWT (HS256, `python-jose`), password hashing via `passlib[bcrypt]`, `OAuth2PasswordBearer` scheme pointing at `/api/auth/login` | [backend/app/core/security.py](../../backend/app/core/security.py) |
| Progress tracking | Two tables: `UserProgress` (per user+module status: locked/in_progress/completed + last_accessed) and `LessonProgress` (per user+lesson boolean `completed`). Module completion % is *derived*, not stored: `completed lessons / total lessons in module` ([main.py:279](../../backend/app/main.py#L279)). "Resume" picks the `UserProgress` row with the most recent `last_accessed`. | [backend/app/main.py](../../backend/app/main.py) `_build_module_progress`, `resume_last_module` |
| AI tutor | RAG service (ChromaDB vector store + Gemini embeddings/LLM), grounded on indexed `Module`/`Lesson` content | [backend/app/services/rag_service.py](../../backend/app/services/rag_service.py) |
| Frontend | Angular 21 | [frontend/](../../frontend) |
| Content authoring | Hard-coded Python dict in `seed_data.py`, upserted idempotently on API startup (`startup_event` → `_seed_module`) | [backend/app/seed_data.py](../../backend/app/seed_data.py) |

**Key implication for this feature:** there is no separate "Topic" entity — `Lesson` already is the topic-level unit the spec's examples describe (see spec.md §2). The diagnostic feature is additive: new tables + a scoring service + a handful of endpoints; it does not change the meaning of any existing column.

## 2. Database Schema Changes

### 2.1 New tables

```python
class DiagnosticQuestion(Base):
    __tablename__ = "diagnostic_questions"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    question_type = Column(String, default="single_choice")  # single_choice | multi_choice
    choices = Column(Text, nullable=False)   # JSON-encoded list[str]; SQLite has no native array/JSON column here
    correct_choices = Column(Text, nullable=False)  # JSON-encoded list[int] (indices into choices)
    points = Column(Integer, default=1, nullable=False)

    lesson = relationship("Lesson")


class DiagnosticAttempt(Base):
    __tablename__ = "diagnostic_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)  # null = track-wide diagnostic; set = module-scoped (FR-D9)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    answers = relationship("DiagnosticAnswer", back_populates="attempt", cascade="all, delete-orphan")


class DiagnosticAnswer(Base):
    __tablename__ = "diagnostic_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),)

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("diagnostic_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("diagnostic_questions.id"), nullable=False)
    selected_choices = Column(Text, nullable=False)  # JSON-encoded list[int]
    points_earned = Column(Integer, default=0, nullable=False)

    attempt = relationship("DiagnosticAttempt", back_populates="answers")
    question = relationship("DiagnosticQuestion")


class MasteryBand(str, enum.Enum):
    MASTERED = "mastered"
    PARTIALLY_MASTERED = "partially_mastered"
    NEEDS_LEARNING = "needs_learning"


class TopicMastery(Base):
    """Current derived mastery per (user, lesson) — the read model the
    recommendation logic and progress-skip logic query. Recomputed (upserted)
    whenever a new diagnostic attempt is submitted for that lesson."""
    __tablename__ = "topic_mastery"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_mastery"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    score = Column(Integer, nullable=False)          # 0-100
    band = Column(String, nullable=False)            # MasteryBand value
    source_attempt_id = Column(Integer, ForeignKey("diagnostic_attempts.id"), nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    lesson = relationship("Lesson")
```

### 2.2 Change to an existing table

`LessonProgress` gains one nullable column so diagnostic-driven completions are distinguishable from manual ones (see research.md §3 for why this is a column, not a new status enum):

```python
class LessonProgress(Base):
    ...
    completion_source = Column(String, nullable=True)  # "manual" | "diagnostic"; null = legacy/manual rows predating this feature
```

### 2.3 Migration approach

The project currently has **no migration tool** — `models.Base.metadata.create_all(bind=engine)` runs on every startup ([main.py:21](../../backend/app/main.py#L21)), which only *adds* new tables/columns is not actually true for SQLite column additions (SQLAlchemy's `create_all` never alters existing tables). Concretely:
- New tables (`DiagnosticQuestion`, `DiagnosticAttempt`, `DiagnosticAnswer`, `TopicMastery`) will be created automatically by `create_all` — no action needed.
- The new `LessonProgress.completion_source` column will **not** be added to the existing `sql_app.db` file automatically. Since this is a dev-stage SQLite file (no production data to preserve per the project's current state), the plan is to add a small startup guard that checks for the column via `PRAGMA table_info(lesson_progress)` and issues `ALTER TABLE lesson_progress ADD COLUMN completion_source TEXT` if missing — the same lightweight, no-framework pattern already used for idempotent seeding in this codebase. Introducing Alembic is out of scope for this feature (separate, standalone infra task) but flagged as a recommended follow-up once schema changes become frequent.

## 3. Backend/API Design

All new endpoints follow the existing conventions exactly: FastAPI path functions in `main.py` (or a new `diagnostics.py` router included into the app, to keep `main.py` from growing further — recommended given `main.py` is already 488 lines), Pydantic schemas in `schemas.py`, JWT auth via `Depends(get_current_user)`.

### 3.1 New Pydantic schemas (schemas.py)

```python
class DiagnosticQuestionOut(BaseModel):
    id: int
    lesson_id: int
    prompt: str
    question_type: str
    choices: List[str]

    class Config:
        from_attributes = True

class DiagnosticStartOut(BaseModel):
    attempt_id: int
    questions: List[DiagnosticQuestionOut]

class DiagnosticAnswerIn(BaseModel):
    question_id: int
    selected_choices: List[int]

class DiagnosticSubmitIn(BaseModel):
    answers: List[DiagnosticAnswerIn]

class TopicMasteryOut(BaseModel):
    lesson_id: int
    lesson_title: str
    score: int
    band: str  # mastered | partially_mastered | needs_learning

class DiagnosticResultOut(BaseModel):
    attempt_id: int
    topic_mastery: List[TopicMasteryOut]
    recommended_start_lesson_id: Optional[int]
    recommended_start_lesson_title: Optional[str]
    auto_completed_lesson_ids: List[int]  # lessons marked complete via mastery
```

### 3.2 New endpoints

| Method & path | Purpose |
|---|---|
| `GET /api/tracks/{track_id}/diagnostic/status` | Has this user taken a diagnostic for this track? Returns last attempt summary or `null`. Used to decide whether to prompt on first entry (FR-D1). |
| `POST /api/tracks/{track_id}/diagnostic/start` | Creates a `DiagnosticAttempt` (module_id=null), returns the question set (all lessons in the track). |
| `POST /api/modules/{module_id}/diagnostic/start` | Same, scoped to one module's lessons (FR-D9). |
| `POST /api/diagnostic/attempts/{attempt_id}/submit` | Body: `DiagnosticSubmitIn`. Scores answers, upserts `TopicMastery`, auto-completes `LessonProgress` for Mastered lessons (respecting FR-D10), computes recommendation. Returns `DiagnosticResultOut`. |
| `GET /api/tracks/{track_id}/recommendation` | Recomputes/returns the current recommended starting lesson without requiring a new attempt (used by the "resume"/dashboard view). |
| `GET /api/tracks/{track_id}/mastery` | Full per-topic mastery breakdown for the current user across the track (used by the student profile page — added when that page was built; only lessons with an actual diagnostic result are included). |

### 3.3 Scoring service (new module: `backend/app/services/diagnostic_service.py`)

Pure functions, unit-testable without the DB where possible:

```python
def score_attempt(attempt: DiagnosticAttempt, db: Session) -> dict[int, TopicScoreResult]:
    """Group the attempt's answers by lesson_id, sum points_earned / points
    available per lesson, return {lesson_id: (score_pct, band)}."""

def classify(score_pct: float) -> MasteryBand:
    if score_pct >= 80: return MasteryBand.MASTERED
    if score_pct >= 60: return MasteryBand.PARTIALLY_MASTERED
    return MasteryBand.NEEDS_LEARNING

def recommend_start(lessons_in_order: list[Lesson], mastery_by_lesson: dict[int, TopicMastery]) -> Optional[Lesson]:
    """First lesson not in MASTERED band; falls back to last lesson if all mastered."""

def apply_mastery_to_progress(db: Session, user_id: int, mastery_results: dict, attempt_id: int) -> list[int]:
    """For each MASTERED lesson, upsert LessonProgress.completed=True,
    completion_source='diagnostic' — but ONLY if no existing completed=True
    row exists yet (FR-D10: never revert manual completions, never let a
    later lower-scoring retake un-complete something)."""
```

This isolates the one genuinely new piece of business logic from the FastAPI route glue, matching the existing separation where `rag_service.py` holds RAG logic out of `main.py`.

## 4. Authentication (clarification, no changes required)

No changes to auth are needed for this feature — it's called out explicitly since the request asked to clarify the technique. Current mechanism:
- **Registration/login:** `POST /api/auth/register` and `POST /api/auth/login` in [main.py](../../backend/app/main.py#L175-L206); passwords hashed with bcrypt via `passlib`.
- **Session mechanism:** stateless JWT (HS256), 24-hour expiry, signed with `JWT_SECRET_KEY` env var (default dev secret — **flagging as a pre-existing risk**, not introduced by this feature, that `dev-secret-change-me` must be overridden via env var in any real deployment).
- **Authorization on requests:** `OAuth2PasswordBearer` extracts the bearer token; `get_current_user` decodes/validates it and loads the `User` row. All new diagnostic endpoints will use `current_user: models.User = Depends(get_current_user)` identically to every existing progress/chat endpoint — diagnostic data is always scoped to `current_user.id`, mirroring how `LessonProgress`/`UserProgress` are scoped today.

## 5. Progress Tracking — how completion is determined (clarification + this feature's integration)

**Today:** `LessonProgress.completed` (bool, manually toggled by the student via `PUT /api/progress/lessons/{lesson_id}`) is the atomic fact. `ModuleProgressOut.completion_percentage` is *computed on read* as `completed lessons / total lessons in module` ([main.py:279](../../backend/app/main.py#L279)) — never stored. `UserProgress.status` (locked/in_progress/completed) is derived and stored per-module, flipped to `completed` when the percentage hits 100 ([main.py:355-359](../../backend/app/main.py#L355-L359)). "Resume" is simply "the `UserProgress` row with the latest `last_accessed`."

**With this feature:** the *only* change is that `LessonProgress.completed` can now become `True` via two sources instead of one — student action (`completion_source="manual"`) or diagnostic mastery (`completion_source="diagnostic"`). Every downstream computation (`completion_percentage`, `UserProgress.status`, resume) is untouched because they only ever read the boolean, not the source. This is the direct payoff of the schema choice in research.md §3: adaptivity slots into the existing completion math with zero changes to it.

## 6. Frontend Integration Points (Angular)

1. On track/module entry, call `GET /api/tracks/{id}/diagnostic/status`; if `null`, show a banner offering the diagnostic (with a visible skip/dismiss option per FR-D11) — implemented on the track map.
2. Diagnostic-taking view: fetch questions from `start`, submit to `submit`, render `DiagnosticResultOut` as a summary screen ("Mastered: 2, Partially mastered: 1, Needs learning: 2 — recommended start: Conditional Statements") before routing into the track map — implemented as `DiagnosticAssessmentComponent` at `/dashboard/diagnostic`.
3. Track/module map: lessons with `completion_source="diagnostic"` render a distinct badge/icon ("auto", with a tooltip) instead of the plain "completed" checkmark, and remain clickable (FR-D12) — implemented in `ModuleViewComponent`.
4. Student profile page (`/profile`, `ProfileComponent`) additionally surfaces the full per-topic mastery breakdown via `GET /api/tracks/{id}/mastery`, with a link to (re)take the diagnostic — added after the initial rollout, alongside the global header/footer.

## 7. Testing Strategy

- Unit tests for `diagnostic_service.classify` (boundary values: exactly 80, exactly 60, exactly 59) and `recommend_start` (all mastered, none mastered, mixed, empty lesson list) — implemented in `backend/tests/test_diagnostic_service.py`.
- Integration test: submit a full attempt via the API, assert `TopicMastery` rows and `LessonProgress.completed`/`completion_source` land correctly, assert a manually-completed lesson is not reverted by a subsequent low-scoring diagnostic retake (FR-D10 regression guard) — verified via a scripted `TestClient` run during implementation; not yet a committed automated test because `app.main` hard-imports `rag_service`, which hard-imports `langchain`/`chromadb` at module load time (a pre-existing constraint, not introduced by this feature).
- `pytest` was added to `requirements.txt` specifically to support the unit tests above (no test framework existed in this repo before this feature).

## 8. Rollout Sequencing (as actually built)

1. Schema + migration guard (§2).
2. Scoring service + unit tests (§3.3, §7).
3. Endpoints + schemas (§3.1–3.2), extracted into `routers/diagnostics.py`.
4. Diagnostic question bank for the first 5 "Python Programming" module lessons in `seed_data.py`.
5. Frontend: diagnostic banner + result screen + badges (§6, items 1–3).
6. Follow-up (separate request): global header/footer, student profile page, and the `/mastery` endpoint + `GET /api/auth/me`'s `created_at` field that the profile page needed (§3.2, §6 item 4).
