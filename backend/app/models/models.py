from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Enum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    progress = relationship("UserProgress", back_populates="user")
    lesson_progress = relationship("LessonProgress", back_populates="user")
    chat_history = relationship("ChatMessage", back_populates="user")

class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Programming, Cybersecurity, Data/ML
    description = Column(Text)

    modules = relationship("Module", back_populates="track")

class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"))
    title = Column(String, index=True)
    content = Column(Text) # Main text/lesson content
    order = Column(Integer) # Sequence order in the track
    policy = Column(Text) # Prompt templates/constraints for AI tutor (e.g., Socratic method)

    track = relationship("Track", back_populates="modules")
    user_progress = relationship("UserProgress", back_populates="module")
    chat_messages = relationship("ChatMessage", back_populates="module")
    lessons = relationship("Lesson", back_populates="module")

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    title = Column(String, index=True)
    content = Column(Text)
    order = Column(Integer)

    module = relationship("Module", back_populates="lessons")
    lesson_progress = relationship("LessonProgress", back_populates="lesson")

class ProgressStatus(str, enum.Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_user_module_progress"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    module_id = Column(Integer, ForeignKey("modules.id"))
    status = Column(String, default=ProgressStatus.IN_PROGRESS)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="progress")
    module = relationship("Module", back_populates="user_progress")

class LessonProgress(Base):
    """Per-lesson completion checkmark, tied to a user's account (FR-07)."""
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # "manual" | "diagnostic" | null (legacy rows predating the diagnostic
    # feature). See specs/001-diagnostic-assessment/research.md #3 for why
    # this is a column rather than a new status enum value.
    completion_source = Column(String, nullable=True)

    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="lesson_progress")

class DiagnosticQuestion(Base):
    """A single diagnostic question, tagged to the topic (Lesson) it assesses.

    Reuses `Lesson` as the topic unit instead of a separate `Topic` table —
    see specs/001-diagnostic-assessment/spec.md #2.
    """
    __tablename__ = "diagnostic_questions"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    question_type = Column(String, default="single_choice")  # single_choice | multi_choice
    choices = Column(Text, nullable=False)  # JSON-encoded list[str]
    correct_choices = Column(Text, nullable=False)  # JSON-encoded list[int] (indices into choices)
    points = Column(Integer, default=1, nullable=False)

    lesson = relationship("Lesson")


class DiagnosticAttempt(Base):
    """One diagnostic-taking event. `module_id` is null for a track-wide
    diagnostic (FR-D1) and set for a module-scoped one (FR-D9)."""
    __tablename__ = "diagnostic_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    track = relationship("Track")
    module = relationship("Module")
    answers = relationship("DiagnosticAnswer", back_populates="attempt", cascade="all, delete-orphan")


class DiagnosticAnswer(Base):
    """One answer within an attempt, graded at submission time."""
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
    recommendation logic and progress-skip logic query. Upserted whenever a
    new diagnostic attempt is submitted for that lesson (see
    diagnostic_service.apply_mastery_to_progress)."""
    __tablename__ = "topic_mastery"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_mastery"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    score = Column(Integer, nullable=False)  # 0-100
    band = Column(String, nullable=False)  # MasteryBand value
    source_attempt_id = Column(Integer, ForeignKey("diagnostic_attempts.id"), nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    lesson = relationship("Lesson")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    module_id = Column(Integer, ForeignKey("modules.id"))
    role = Column(String) # user, assistant
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="chat_history")
    module = relationship("Module", back_populates="chat_messages")
