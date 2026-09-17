# Research: Mastery Thresholds & Adaptive-Start Design

## 1. Why 80 / 60 as the cut points

The prompt explicitly allows any thresholds as long as they're justified. Rationale for keeping 80–100 / 60–79 / <60:

1. **Mastery learning literature.** Bloom's mastery-learning model and its modern derivatives (Khan Academy, Duolingo's placement tests) commonly treat ~80% as the point past which a learner reliably applies a skill rather than pattern-matching a few memorized cases. Khan Academy's own "Mastery" system uses 80% correct (with decay checks) as its mastery bar.
2. **Risk asymmetry.** Skipping content is a one-directional risk: a false "Mastered" verdict wastes the student's time later (they hit a gap mid-module), while a false "Needs Learning" verdict only costs them a lesson they already knew — mildly annoying, not harmful. An 80% bar is deliberately conservative (biased toward "make them review it") rather than 70%, which the education-measurement literature (e.g., criterion-referenced testing guidance) treats as a "passing" bar for graded assessment, not a "you can skip re-teaching" bar. Skipping should demand a stricter standard than passing.
3. **Middle band exists to avoid a cliff-edge, binary skip/no-skip decision.** A single 70% cutoff would treat a 71% and a 30% identically (both "start here") and a 69% and 95% identically (both "study fully"). The 60–79 "Partially Mastered" band lets the product surface a cheaper intervention (badge as "quick review" rather than force a full lesson) instead of a binary skip/repeat, which better matches partial-knowledge reality (a student may know 3 of 5 subtopics in a lesson).
4. **Below 60 as "Needs Learning."** 60% is a widely used floor for "did not demonstrate the skill" in criterion-referenced grading (many institutions treat <60% as a failing grade), so it's a legible, defensible floor to reuse here rather than inventing a new number.

These are configurable, not hard-coded assumptions the algorithm depends on — see §4 (implementation note) for making them a single constant/config value so they can be tuned from real completion/mis-skip data once collected (an NFR-worthy follow-up: track "mastered-but-then-struggled" rate per threshold to validate/adjust later).

## 2. Why score at the Lesson (topic) granularity, not Module

Modules bundle multiple topics (e.g., "Python Programming" module contains "Introduction," "Variables," "Conditionals," "Loops," "Functions" as lessons). Scoring only at module granularity would force an all-or-nothing skip of 5 topics based on one aggregate number, defeating the stated goal ("student mastered Topics 1–2, start at Topic 3" — a sub-module recommendation). Lesson-level scoring is the finest granularity the existing schema already tracks completion at (`LessonProgress`), so it reuses the grain the rest of the product already reasons about — no new granularity concept needed.

## 3. Why reuse `LessonProgress.completed` for diagnostic-driven skips instead of a separate "skipped" state

Alternative considered: add a `SKIPPED` status distinct from `COMPLETED`. Rejected because:
- `ModuleProgressOut.completion_percentage` and the resume/unlock logic in [main.py](../../backend/app/main.py) already key entirely off `LessonProgress.completed` (boolean) and `UserProgress.status`. Introducing a third state would require touching every consumer of those fields (frontend progress bars, the `open_module`/`resume` endpoints) to treat `SKIPPED` as "count toward completion but visually distinct."
- Instead, `LessonProgress` gets one additional nullable column, `completion_source` (`"manual" | "diagnostic"`), which is purely informational (drives the "skipped via diagnostic" badge and the FR-D10 "never revert" rule) without changing any existing boolean/percentage math.

## 4. Recommendation algorithm (plain description)

For a given user and track (or module, per FR-D9):
1. Load all lessons in `order`.
2. Load the user's latest `TopicMastery` row per lesson (if any).
3. Walk lessons in order; the **recommended starting lesson** is the first one whose band is not `mastered` (or that has no diagnostic result at all, i.e., insufficient data → treated as not-mastered per spec edge case).
4. If every lesson is `mastered`, recommend the final lesson in order (the UI can layer a "you've mastered this module" message on top).

This is intentionally the simplest correct algorithm (a linear scan), not a prerequisite graph / knowledge-tracing model — the course structure here is already strictly sequential (`order` column, module unlocking), so a graph solver would be solving a problem the schema doesn't have. If prerequisite branching (non-linear topic graphs) is ever introduced, this function is the single seam to replace.

## 5. Configuration, not code, for thresholds

Thresholds live as three module-level constants (or a `diagnostic_config` table if admin-tunability without a deploy is required later — not needed for v1) in the scoring service, e.g.:

```python
MASTERY_THRESHOLDS = {
    "mastered": 80,
    "partially_mastered": 60,
}
```

Kept out of the schema for v1 (YAGNI — no admin UI exists to edit thresholds yet); revisit if instructors need per-track tuning.
