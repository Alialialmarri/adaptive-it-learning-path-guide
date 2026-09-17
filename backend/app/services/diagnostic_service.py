"""Diagnostic scoring and adaptive-start recommendation logic.

Kept separate from the FastAPI route handlers (see routers/diagnostics.py)
the same way rag_service.py holds RAG logic out of main.py. See
specs/001-diagnostic-assessment/plan.md #3.3 and research.md for the
rationale behind the thresholds and the recommendation algorithm.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import models

# Justified in specs/001-diagnostic-assessment/research.md #1.
MASTERY_THRESHOLDS = {
    "mastered": 80,
    "partially_mastered": 60,
}


@dataclass
class TopicScoreResult:
    lesson_id: int
    points_earned: int
    points_possible: int
    score_pct: int
    band: str


def classify(score_pct: float) -> str:
    """FR-D4: classify a 0-100 topic score into a mastery band."""
    if score_pct >= MASTERY_THRESHOLDS["mastered"]:
        return models.MasteryBand.MASTERED.value
    if score_pct >= MASTERY_THRESHOLDS["partially_mastered"]:
        return models.MasteryBand.PARTIALLY_MASTERED.value
    return models.MasteryBand.NEEDS_LEARNING.value


def grade_answer(question: models.DiagnosticQuestion, selected_choices: List[int]) -> int:
    """Full points if the selected set exactly matches the correct set, else 0."""
    correct = set(json.loads(question.correct_choices))
    selected = set(selected_choices)
    return question.points if selected == correct else 0


def score_attempt(db: Session, attempt: models.DiagnosticAttempt) -> Dict[int, TopicScoreResult]:
    """FR-D3: Topic Score = (points earned / points possible) x 100, grouped
    by lesson, using only lessons that had at least one answered question in
    this attempt."""
    rows = (
        db.query(models.DiagnosticAnswer, models.DiagnosticQuestion)
        .join(models.DiagnosticQuestion, models.DiagnosticQuestion.id == models.DiagnosticAnswer.question_id)
        .filter(models.DiagnosticAnswer.attempt_id == attempt.id)
        .all()
    )

    totals: Dict[int, List[int]] = {}
    for answer, question in rows:
        earned, possible = totals.setdefault(question.lesson_id, [0, 0])
        totals[question.lesson_id][0] = earned + answer.points_earned
        totals[question.lesson_id][1] = possible + question.points

    results: Dict[int, TopicScoreResult] = {}
    for lesson_id, (earned, possible) in totals.items():
        score_pct = round((earned / possible) * 100) if possible else 0
        results[lesson_id] = TopicScoreResult(
            lesson_id=lesson_id,
            points_earned=earned,
            points_possible=possible,
            score_pct=score_pct,
            band=classify(score_pct),
        )
    return results


def recommend_start(
    lessons_in_order: List[models.Lesson],
    mastery_by_lesson: Dict[int, models.TopicMastery],
) -> Optional[models.Lesson]:
    """FR-D6: first lesson (in order) that is not Mastered. A lesson with no
    diagnostic result at all is treated as not-mastered (insufficient
    evidence, per the spec's edge cases) rather than assumed mastered.
    Falls back to the last lesson if every lesson is Mastered."""
    if not lessons_in_order:
        return None
    for lesson in lessons_in_order:
        mastery = mastery_by_lesson.get(lesson.id)
        if mastery is None or mastery.band != models.MasteryBand.MASTERED.value:
            return lesson
    return lessons_in_order[-1]


def apply_mastery_to_progress(
    db: Session,
    user_id: int,
    mastery_results: Dict[int, TopicScoreResult],
    attempt_id: int,
) -> List[int]:
    """FR-D5/D7/D10: upsert TopicMastery for every scored lesson, and
    auto-complete LessonProgress for Mastered lessons — but never overwrite
    a lesson that is already marked completed (manually or by an earlier,
    higher-scoring diagnostic), so a later lower-scoring retake can never
    revert progress."""
    auto_completed: List[int] = []
    now = datetime.now(timezone.utc)

    for lesson_id, result in mastery_results.items():
        mastery_row = (
            db.query(models.TopicMastery)
            .filter(models.TopicMastery.user_id == user_id, models.TopicMastery.lesson_id == lesson_id)
            .first()
        )
        if mastery_row is None:
            mastery_row = models.TopicMastery(user_id=user_id, lesson_id=lesson_id)
            db.add(mastery_row)
        mastery_row.score = result.score_pct
        mastery_row.band = result.band
        mastery_row.source_attempt_id = attempt_id
        mastery_row.computed_at = now

        if result.band != models.MasteryBand.MASTERED.value:
            continue

        progress_row = (
            db.query(models.LessonProgress)
            .filter(models.LessonProgress.user_id == user_id, models.LessonProgress.lesson_id == lesson_id)
            .first()
        )
        if progress_row is None:
            db.add(models.LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                completed=True,
                completed_at=now,
                completion_source="diagnostic",
            ))
            auto_completed.append(lesson_id)
        elif not progress_row.completed:
            progress_row.completed = True
            progress_row.completed_at = now
            progress_row.completion_source = "diagnostic"
            auto_completed.append(lesson_id)
        # else: already completed (manual or diagnostic) -> leave untouched (FR-D10).

    db.commit()
    return auto_completed
