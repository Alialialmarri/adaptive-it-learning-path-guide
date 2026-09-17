# Feature Specification: Diagnostic Assessment & Adaptive Starting Point

**Feature branch:** `001-diagnostic-assessment`
**Status:** Draft
**Input:** "Add a diagnostic assessment before starting a course so the system recommends where a student should start, instead of forcing everyone through Module/Topic 1, and apply the same principle across other modules."

## 1. Problem Statement

Today the system (see [docs/reports/requirements.md](../../docs/reports/requirements.md)) tracks *completion* (`UserProgress`, `LessonProgress`) but has no notion of *prior knowledge*. Every learner enters a track at Lesson 1 of Module 1 regardless of what they already know. This makes the system a progress tracker with an AI tutor bolted on, not an adaptive learning system.

This spec adds a **diagnostic assessment** taken once per track (re-takeable on demand) that measures existing knowledge per topic, classifies each topic into a mastery band, and uses those bands to compute a **recommended starting point** and to **pre-mark mastered topics as skippable** throughout the track — not just at the first module.

## 2. Terminology Mapping

The prompt's example ("Topic 1: Python Basics" … "Topic 5: Functions") maps onto this codebase's existing hierarchy as follows, to avoid introducing a redundant concept:

| Prompt term | Existing model | Notes |
|---|---|---|
| Course | `Track` | e.g. "Programming" |
| Topic | `Lesson` | Each `Lesson` already is an ordered, gradable unit of content within a `Module` (e.g. "Variables and Data Types" is a `Lesson` inside the "Python Programming" `Module`). |
| Module | `Module` | A `Module` groups related `Lesson`s (topics). |

Decision: **reuse `Lesson` as the diagnostic/topic unit.** Introducing a separate `Topic` table would duplicate `Lesson` almost exactly (title, order, module_id) and force two parallel taxonomies to stay in sync. All "topic score," "topic mastery," and "recommended starting lesson" language below refers to `Lesson` rows.

## 3. User Scenarios

### Primary story
A student enrolls in the Python track for the first time. Before any module content is shown, the system offers a diagnostic assessment covering the track's lessons (Python Basics, Variables & Data Types, Conditionals, Loops, Functions). The student answers a small set of questions per lesson. The system scores each lesson, classifies it as **Mastered / Partially Mastered / Needs Learning**, and then presents a recommended path: "You've mastered Python Basics and Variables. We recommend starting at Conditional Statements." Mastered lessons are shown as already checked off (with a "why" tooltip: "Skipped via diagnostic — scored 92%"), but remain fully accessible if the student wants to revisit them.

### Acceptance scenarios
1. **Given** a student has never taken the Python diagnostic, **when** they open the Python track for the first time, **then** they are prompted to take the diagnostic before the normal module view loads, with an explicit "Skip and start from the beginning" option.
2. **Given** a student scores 92% on the "Python Basics" lesson questions and 55% on "Functions", **when** the diagnostic is scored, **then** "Python Basics" is marked Mastered and pre-completed, "Functions" is marked Needs Learning and left untouched, and the recommended starting lesson is the first lesson that is not Mastered.
3. **Given** a student mastered lessons in Module 1 but not Module 2, **when** they finish Module 1 (whether by skipping or by studying), **then** the system's "resume" recommendation for Module 2 also honors that module's own diagnostic results (same principle applied per module, not only at track entry).
4. **Given** a student wants to challenge a "Needs Learning" verdict, **when** they open a mastered-and-skipped lesson anyway, **then** they can still study it and mark it complete manually; diagnostic mastery never locks content, it only changes defaults and recommendations.
5. **Given** a student retakes the diagnostic later (e.g., after months away), **when** they submit new answers, **then** topic mastery is recalculated and the recommendation updates; previously completed lessons (via manual study) are never un-completed by a new diagnostic result.

### Edge cases
- A lesson has zero diagnostic questions authored yet → treat as "insufficient data," fall back to Needs Learning (never assume mastery from absence of evidence).
- Student abandons the diagnostic partway → partial submission is scored only for answered lessons; unanswered lessons default to Needs Learning; student can resume or retake before starting the course.
- Student already has manual progress (started mid-course before this feature shipped) → diagnostic is offered but never downgrades a lesson already marked `completed`.

## 4. Functional Requirements

- **FR-D1:** The system shall allow an authenticated student to start a diagnostic assessment for a track they have not yet completed a diagnostic for.
- **FR-D2:** The diagnostic shall be composed of questions, each tagged to exactly one `Lesson` (topic) and carrying a point value.
- **FR-D3:** Upon submission, the system shall compute a **Topic Score** per lesson: `(points earned on that lesson's questions / total points available for that lesson) × 100`, using only lessons that had at least one answered question.
- **FR-D4:** The system shall classify each scored topic into one of three mastery bands (thresholds justified in [research.md](./research.md)):
  - **80–100% → Mastered**
  - **60–79% → Partially Mastered**
  - **0–59% → Needs Learning**
- **FR-D5:** The system shall persist the diagnostic result per (user, lesson): score, band, and timestamp, independent of normal lesson-completion tracking.
- **FR-D6:** The system shall compute a **recommended starting lesson** per track/module: the first lesson in `order` that is *not* Mastered. If all lessons are Mastered, recommend the last lesson (or a "you're ready for an assessment/project" state — out of scope for v1, but the API must not error).
- **FR-D7:** Mastered lessons shall be automatically marked `completed` in `LessonProgress` (attributed to the diagnostic, not manual study) so existing progress-percentage and resume logic (FR-07/FR-08/FR-09) reflect the skip without any duplicated logic.
- **FR-D8:** Partially Mastered lessons shall NOT be auto-completed, but shall be flagged in the API response so the frontend can badge them ("Quick review recommended") — full study is still expected.
- **FR-D9:** The "same principle" shall apply per module: a student can (re-)take a shorter, module-scoped diagnostic when entering any module for the first time, not only once at track enrollment. The scoring/classification/recommendation logic (FR-D3–D7) is identical; only the question scope (module's lessons vs. all track lessons) differs.
- **FR-D10:** A diagnostic-driven auto-completion shall never overwrite a lesson already marked `completed` by the student, and a later, lower-scoring diagnostic retake shall never revert an already-completed lesson to incomplete.
- **FR-D11:** The student shall always be able to bypass or ignore the diagnostic and start from Lesson 1, and can retake a diagnostic at any time.
- **FR-D12:** The frontend must clearly disclose that a lesson was skipped due to the diagnostic and expose a one-click way to open it anyway.

## 5. Non-Functional Requirements

- **NFR-D1:** Diagnostic scoring is synchronous and must complete in under 1 second for a track-sized question set (~30–50 questions), matching existing API latency expectations.
- **NFR-D2:** Diagnostic questions and answers are versionable content (authored like `Module`/`Lesson` content today) — no new authoring tool is required for v1; questions are seeded the same way `seed_data.py` seeds modules/lessons.
- **NFR-D3:** All new endpoints require the existing JWT bearer auth (`get_current_user`) — no unauthenticated diagnostic data.

## 6. Key Entities (conceptual — see plan.md for schema)

- **DiagnosticQuestion**: belongs to a `Lesson`; has prompt, choices, correct answer(s), point value.
- **DiagnosticAttempt**: one per (user, track) submission event; has a timestamp and overall status.
- **DiagnosticAnswer**: one per (attempt, question); records what the student answered and points earned.
- **TopicMastery**: one per (user, lesson), the *current* derived state (score, band, source attempt, computed_at) — this is the read model the rest of the app (recommendations, progress skip) queries; recomputed on each new attempt.

## 7. Out of Scope (v1)

- Adaptive question difficulty *within* the diagnostic (e.g., IRT/CAT-style branching). v1 uses a fixed question bank per lesson.
- Automated question generation via the RAG/LLM pipeline (could be a v2 enhancement — author questions manually in `seed_data.py` for now, same pattern as lesson content).
- Cross-track skill transfer (e.g., mastering "Loops" in Python informing the Cybersecurity track).
