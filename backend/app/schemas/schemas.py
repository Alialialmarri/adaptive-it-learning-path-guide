from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LessonBase(BaseModel):
    title: str
    content: str
    order: int

class LessonCreate(LessonBase):
    module_id: int

class Lesson(LessonBase):
    id: int
    module_id: int

    class Config:
        from_attributes = True

class ModuleBase(BaseModel):
    title: str
    content: Optional[str] = None
    order: int
    policy: Optional[str] = None

class ModuleCreate(ModuleBase):
    track_id: int

class Module(ModuleBase):
    id: int
    track_id: int
    lessons: List[Lesson] = []

    class Config:
        from_attributes = True


class LessonCompletionUpdate(BaseModel):
    completed: bool


class ModuleProgressOut(BaseModel):
    module_id: int
    status: str
    completion_percentage: int
    completed_lesson_ids: List[int]
    # Subset of completed_lesson_ids that were auto-completed by the
    # diagnostic assessment rather than studied manually (FR-D12).
    diagnostic_completed_lesson_ids: List[int] = []
    last_accessed: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumeModuleOut(BaseModel):
    module_id: int
    module_title: str
    status: str
    last_accessed: Optional[datetime] = None


class ChatMessageOut(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ChatHistorySummaryOut(BaseModel):
    module_id: int
    module_title: str
    last_message_at: datetime

    class Config:
        from_attributes = True


# --- Diagnostic Assessment (specs/001-diagnostic-assessment) ---

class DiagnosticQuestionOut(BaseModel):
    id: int
    lesson_id: int
    prompt: str
    question_type: str
    choices: List[str]


class DiagnosticStartOut(BaseModel):
    attempt_id: int
    scope: str  # "track" | "module"
    questions: List[DiagnosticQuestionOut]


class DiagnosticAnswerIn(BaseModel):
    question_id: int
    selected_choices: List[int]


class DiagnosticSubmitIn(BaseModel):
    answers: List[DiagnosticAnswerIn]


class TopicMasteryOut(BaseModel):
    lesson_id: int
    lesson_title: str
    module_id: int
    module_title: str
    score: int
    band: str  # mastered | partially_mastered | needs_learning


class DiagnosticResultOut(BaseModel):
    attempt_id: int
    topic_mastery: List[TopicMasteryOut]
    recommended_start_lesson_id: Optional[int] = None
    recommended_start_lesson_title: Optional[str] = None
    recommended_start_module_id: Optional[int] = None
    recommended_start_module_title: Optional[str] = None
    auto_completed_lesson_ids: List[int] = []


class DiagnosticStatusOut(BaseModel):
    attempt_id: int
    submitted_at: Optional[datetime] = None


class RecommendationOut(BaseModel):
    recommended_start_lesson_id: Optional[int] = None
    recommended_start_lesson_title: Optional[str] = None
    recommended_start_module_id: Optional[int] = None
    recommended_start_module_title: Optional[str] = None
