"""Unit tests for the diagnostic scoring/recommendation logic
(specs/001-diagnostic-assessment). These test the pure functions in
diagnostic_service.py directly with lightweight fakes, so they don't need a
database session or the RAG service's heavy dependencies (langchain/
chromadb) to run.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import models
from app.services.diagnostic_service import classify, grade_answer, recommend_start


# --- classify() boundaries (FR-D4 / research.md #1) ---

def test_classify_mastered_at_and_above_80():
    assert classify(100) == models.MasteryBand.MASTERED.value
    assert classify(80) == models.MasteryBand.MASTERED.value


def test_classify_partially_mastered_between_60_and_79():
    assert classify(79) == models.MasteryBand.PARTIALLY_MASTERED.value
    assert classify(60) == models.MasteryBand.PARTIALLY_MASTERED.value


def test_classify_needs_learning_below_60():
    assert classify(59) == models.MasteryBand.NEEDS_LEARNING.value
    assert classify(0) == models.MasteryBand.NEEDS_LEARNING.value


# --- grade_answer() ---

class _FakeQuestion:
    def __init__(self, correct_choices, points=1):
        self.correct_choices = json.dumps(correct_choices)
        self.points = points


def test_grade_answer_awards_full_points_on_exact_match():
    q = _FakeQuestion([1], points=2)
    assert grade_answer(q, [1]) == 2


def test_grade_answer_awards_zero_on_wrong_choice():
    q = _FakeQuestion([1])
    assert grade_answer(q, [0]) == 0


def test_grade_answer_multi_choice_requires_exact_set_match():
    q = _FakeQuestion([0, 2], points=3)
    assert grade_answer(q, [0, 2]) == 3
    assert grade_answer(q, [2, 0]) == 3  # order doesn't matter
    assert grade_answer(q, [0]) == 0  # partial selection doesn't earn partial credit


# --- recommend_start() (FR-D6 / research.md #4) ---

class _FakeLesson:
    def __init__(self, id):
        self.id = id


class _FakeMastery:
    def __init__(self, band):
        self.band = band


def test_recommend_start_empty_lesson_list_returns_none():
    assert recommend_start([], {}) is None


def test_recommend_start_no_mastery_data_recommends_first_lesson():
    lessons = [_FakeLesson(1), _FakeLesson(2)]
    assert recommend_start(lessons, {}).id == 1


def test_recommend_start_skips_mastered_prefix():
    lessons = [_FakeLesson(1), _FakeLesson(2), _FakeLesson(3)]
    mastery = {1: _FakeMastery("mastered"), 2: _FakeMastery("mastered")}
    assert recommend_start(lessons, mastery).id == 3


def test_recommend_start_stops_at_first_partially_mastered_or_needs_learning():
    lessons = [_FakeLesson(1), _FakeLesson(2), _FakeLesson(3)]
    mastery = {
        1: _FakeMastery("mastered"),
        2: _FakeMastery("partially_mastered"),
        3: _FakeMastery("mastered"),
    }
    assert recommend_start(lessons, mastery).id == 2


def test_recommend_start_all_mastered_falls_back_to_last_lesson():
    lessons = [_FakeLesson(1), _FakeLesson(2)]
    mastery = {1: _FakeMastery("mastered"), 2: _FakeMastery("mastered")}
    assert recommend_start(lessons, mastery).id == 2


def test_recommend_start_missing_mastery_row_treated_as_not_mastered():
    # A lesson with no diagnostic result at all (e.g. unanswered) must never
    # be assumed mastered — see spec.md's "insufficient data" edge case.
    lessons = [_FakeLesson(1), _FakeLesson(2)]
    mastery = {1: _FakeMastery("mastered")}
    assert recommend_start(lessons, mastery).id == 2
