"""Diagnostic assessment endpoints (specs/001-diagnostic-assessment).

Extracted into its own router rather than added to main.py, which was
already ~490 lines before this feature (see plan.md #3).
"""
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..db.database import get_db
from ..models import models
from ..schemas import schemas
from ..services import diagnostic_service

router = APIRouter(tags=["diagnostics"])


def _lessons_for_track(db: Session, track_id: int) -> List[models.Lesson]:
    return (
        db.query(models.Lesson)
        .join(models.Module, models.Module.id == models.Lesson.module_id)
        .filter(models.Module.track_id == track_id)
        .order_by(models.Module.order, models.Lesson.order)
        .all()
    )


def _lessons_for_module(db: Session, module_id: int) -> List[models.Lesson]:
    return (
        db.query(models.Lesson)
        .filter(models.Lesson.module_id == module_id)
        .order_by(models.Lesson.order)
        .all()
    )


def _latest_mastery_by_lesson(
    db: Session, user_id: int, lesson_ids: List[int]
) -> Dict[int, models.TopicMastery]:
    if not lesson_ids:
        return {}
    rows = (
        db.query(models.TopicMastery)
        .filter(models.TopicMastery.user_id == user_id, models.TopicMastery.lesson_id.in_(lesson_ids))
        .all()
    )
    return {row.lesson_id: row for row in rows}


def _question_out(question: models.DiagnosticQuestion) -> schemas.DiagnosticQuestionOut:
    return schemas.DiagnosticQuestionOut(
        id=question.id,
        lesson_id=question.lesson_id,
        prompt=question.prompt,
        question_type=question.question_type,
        choices=json.loads(question.choices),
    )


def _start_attempt(
    db: Session,
    user_id: int,
    track_id: int,
    module_id: Optional[int],
    lessons: List[models.Lesson],
    scope: str,
) -> schemas.DiagnosticStartOut:
    if not lessons:
        raise HTTPException(status_code=404, detail="No lessons found for this diagnostic scope")

    lesson_ids = [lesson.id for lesson in lessons]
    questions = (
        db.query(models.DiagnosticQuestion)
        .filter(models.DiagnosticQuestion.lesson_id.in_(lesson_ids))
        .order_by(models.DiagnosticQuestion.id)
        .all()
    )
    if not questions:
        # Edge case from spec.md #3: a lesson with zero authored questions
        # yet is "insufficient data", not an error state for the caller —
        # but starting a diagnostic with nothing to ask is still a 404.
        raise HTTPException(status_code=404, detail="No diagnostic questions are available for this scope yet")

    # Present questions grouped by topic in the same order the track/module
    # teaches them, not DB insertion order, so the diagnostic reads the same
    # "Topic 1, Topic 2, ..." way the spec's example does.
    lesson_order = {lesson.id: index for index, lesson in enumerate(lessons)}
    questions.sort(key=lambda q: (lesson_order.get(q.lesson_id, len(lessons)), q.id))

    attempt = models.DiagnosticAttempt(user_id=user_id, track_id=track_id, module_id=module_id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return schemas.DiagnosticStartOut(
        attempt_id=attempt.id,
        scope=scope,
        questions=[_question_out(q) for q in questions],
    )


def _recommendation_for_lessons(
    db: Session, user_id: int, lessons: List[models.Lesson]
) -> schemas.RecommendationOut:
    mastery_by_lesson = _latest_mastery_by_lesson(db, user_id, [lesson.id for lesson in lessons])
    recommended = diagnostic_service.recommend_start(lessons, mastery_by_lesson)
    if recommended is None:
        return schemas.RecommendationOut()
    return schemas.RecommendationOut(
        recommended_start_lesson_id=recommended.id,
        recommended_start_lesson_title=recommended.title,
        recommended_start_module_id=recommended.module_id,
        recommended_start_module_title=recommended.module.title,
    )


@router.get("/tracks/{track_id}/diagnostic/status", response_model=Optional[schemas.DiagnosticStatusOut])
def get_diagnostic_status(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """FR-D1: has this user already taken the track-wide diagnostic? Used by
    the frontend to decide whether to prompt for it on first entry."""
    attempt = (
        db.query(models.DiagnosticAttempt)
        .filter(
            models.DiagnosticAttempt.user_id == current_user.id,
            models.DiagnosticAttempt.track_id == track_id,
            models.DiagnosticAttempt.module_id.is_(None),
            models.DiagnosticAttempt.submitted_at.isnot(None),
        )
        .order_by(models.DiagnosticAttempt.submitted_at.desc())
        .first()
    )
    if attempt is None:
        return None
    return schemas.DiagnosticStatusOut(attempt_id=attempt.id, submitted_at=attempt.submitted_at)


@router.post("/tracks/{track_id}/diagnostic/start", response_model=schemas.DiagnosticStartOut)
def start_track_diagnostic(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    lessons = _lessons_for_track(db, track_id)
    return _start_attempt(db, current_user.id, track_id, None, lessons, scope="track")


@router.post("/modules/{module_id}/diagnostic/start", response_model=schemas.DiagnosticStartOut)
def start_module_diagnostic(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """FR-D9: same principle applied per module, not only at track entry."""
    module = db.query(models.Module).filter(models.Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    lessons = _lessons_for_module(db, module_id)
    return _start_attempt(db, current_user.id, module.track_id, module_id, lessons, scope="module")


@router.post("/diagnostic/attempts/{attempt_id}/submit", response_model=schemas.DiagnosticResultOut)
def submit_diagnostic(
    attempt_id: int,
    submission: schemas.DiagnosticSubmitIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    attempt = db.query(models.DiagnosticAttempt).filter(models.DiagnosticAttempt.id == attempt_id).first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Diagnostic attempt not found")
    if attempt.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This diagnostic attempt belongs to another user")
    if attempt.submitted_at is not None:
        raise HTTPException(status_code=400, detail="This diagnostic attempt was already submitted")

    question_ids = [a.question_id for a in submission.answers]
    questions_by_id = {
        q.id: q
        for q in db.query(models.DiagnosticQuestion).filter(models.DiagnosticQuestion.id.in_(question_ids)).all()
    }

    for answer_in in submission.answers:
        question = questions_by_id.get(answer_in.question_id)
        if question is None:
            continue  # ignore unknown/stale question ids rather than fail the whole submission
        points_earned = diagnostic_service.grade_answer(question, answer_in.selected_choices)
        db.add(models.DiagnosticAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_choices=json.dumps(answer_in.selected_choices),
            points_earned=points_earned,
        ))

    attempt.submitted_at = datetime.now(timezone.utc)
    db.commit()

    mastery_results = diagnostic_service.score_attempt(db, attempt)
    auto_completed = diagnostic_service.apply_mastery_to_progress(
        db, current_user.id, mastery_results, attempt.id
    )

    lessons = (
        _lessons_for_track(db, attempt.track_id)
        if attempt.module_id is None
        else _lessons_for_module(db, attempt.module_id)
    )
    recommendation = _recommendation_for_lessons(db, current_user.id, lessons)

    lesson_by_id = {lesson.id: lesson for lesson in lessons}
    topic_mastery_out = [
        schemas.TopicMasteryOut(
            lesson_id=lesson_id,
            lesson_title=lesson_by_id[lesson_id].title if lesson_id in lesson_by_id else "",
            module_id=lesson_by_id[lesson_id].module_id if lesson_id in lesson_by_id else 0,
            module_title=lesson_by_id[lesson_id].module.title if lesson_id in lesson_by_id else "",
            score=result.score_pct,
            band=result.band,
        )
        for lesson_id, result in mastery_results.items()
        if lesson_id in lesson_by_id
    ]
    topic_mastery_out.sort(key=lambda t: (t.module_id, t.lesson_id))

    return schemas.DiagnosticResultOut(
        attempt_id=attempt.id,
        topic_mastery=topic_mastery_out,
        recommended_start_lesson_id=recommendation.recommended_start_lesson_id,
        recommended_start_lesson_title=recommendation.recommended_start_lesson_title,
        recommended_start_module_id=recommendation.recommended_start_module_id,
        recommended_start_module_title=recommendation.recommended_start_module_title,
        auto_completed_lesson_ids=auto_completed,
    )


@router.get("/tracks/{track_id}/mastery", response_model=List[schemas.TopicMasteryOut])
def get_track_mastery(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Full per-topic mastery breakdown for the student's profile page --
    only lessons with an actual diagnostic result are included (lessons
    never assessed simply don't appear, rather than showing a fabricated
    0% for something the student was never asked about)."""
    track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    lessons = _lessons_for_track(db, track_id)
    mastery_by_lesson = _latest_mastery_by_lesson(db, current_user.id, [lesson.id for lesson in lessons])

    result = []
    for lesson in lessons:
        mastery = mastery_by_lesson.get(lesson.id)
        if mastery is None:
            continue
        result.append(schemas.TopicMasteryOut(
            lesson_id=lesson.id,
            lesson_title=lesson.title,
            module_id=lesson.module_id,
            module_title=lesson.module.title,
            score=mastery.score,
            band=mastery.band,
        ))
    return result


@router.get("/tracks/{track_id}/recommendation", response_model=schemas.RecommendationOut)
def get_track_recommendation(
    track_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Recompute/return the current recommended starting lesson without
    requiring a new diagnostic attempt (used by the dashboard/resume view)."""
    track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    lessons = _lessons_for_track(db, track_id)
    return _recommendation_for_lessons(db, current_user.id, lessons)
