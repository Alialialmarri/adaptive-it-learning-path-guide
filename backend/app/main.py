from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from .db.database import SessionLocal, engine, Base
from .models import models
from .schemas import schemas
from . import seed_data
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .services.rag_service import RAGService, RAGNotConfiguredError
from .core.security import hash_password, verify_password, create_access_token, get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import os
import threading

load_dotenv()

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Initialize RAG Service
# Use 'data' directory for raw files and 'chroma_db' for vector store
rag_service = RAGService(data_dir="./data", persist_dir="./chroma_db")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def index_module_content(db: Session):
    """Index all module and lesson content into RAG."""
    modules = db.query(models.Module).all()
    lessons = db.query(models.Lesson).all()
    
    print("Indexing content...")
    for module in modules:
        content = f"Module: {module.title}\nContent: {module.content}"
        try:
            rag_service.ingest_text(content, metadata={"type": "module", "id": module.id, "title": module.title, "module_id": module.id})
        except Exception as e:
            print(f"Warning: failed to index module '{module.title}': {e}")
        
    for lesson in lessons:
        content = f"Lesson: {lesson.title} (Module: {lesson.module.title})\nContent: {lesson.content}"
        try:
            rag_service.ingest_text(content, metadata={"type": "lesson", "id": lesson.id, "title": lesson.title, "module_id": lesson.module_id})
        except Exception as e:
            print(f"Warning: failed to index lesson '{lesson.title}': {e}")
    print("Content indexing complete.")

def deduplicate_lessons(db: Session):
    duplicates = (
        db.query(models.Lesson.module_id, models.Lesson.title, func.count(models.Lesson.id).label("cnt"))
        .group_by(models.Lesson.module_id, models.Lesson.title)
        .having(func.count(models.Lesson.id) > 1)
        .all()
    )

    if not duplicates:
        return

    for module_id, title, _ in duplicates:
        lessons = (
            db.query(models.Lesson)
            .filter(models.Lesson.module_id == module_id, models.Lesson.title == title)
            .order_by(models.Lesson.id.asc())
            .all()
        )
        for lesson in lessons[1:]:
            db.delete(lesson)

    db.commit()

def _seed_module(db: Session, track: models.Track, module_spec: dict) -> None:
    module = db.query(models.Module).filter(models.Module.title == module_spec["title"]).first()
    if module is None:
        module = models.Module(
            title=module_spec["title"],
            content=module_spec["content"],
            order=module_spec["order"],
            policy=module_spec["policy"],
            track_id=track.id,
        )
        db.add(module)
        db.commit()
        db.refresh(module)
        print(f"Seeded '{module_spec['title']}' module.")
    else:
        module.content = module_spec["content"]
        module.order = module_spec["order"]
        module.policy = module_spec["policy"]
        module.track_id = track.id
        db.commit()

    lessons_data = module_spec["lessons"]
    desired_titles = {l["title"] for l in lessons_data}
    existing_lessons = db.query(models.Lesson).filter(models.Lesson.module_id == module.id).all()
    for l in existing_lessons:
        if l.title not in desired_titles:
            db.delete(l)

    for lesson_data in lessons_data:
        existing_lesson = db.query(models.Lesson).filter(
            models.Lesson.module_id == module.id,
            models.Lesson.title == lesson_data["title"]
        ).first()
        if existing_lesson:
            existing_lesson.order = lesson_data["order"]
            existing_lesson.content = lesson_data["content"]
        else:
            db.add(
                models.Lesson(
                    module_id=module.id,
                    title=lesson_data["title"],
                    order=lesson_data["order"],
                    content=lesson_data["content"]
                )
            )

    db.commit()
    print(f"Seeded lessons for '{module_spec['title']}'.")


def _index_content_in_background():
    """Runs off the startup critical path: indexing calls the Gemini embeddings
    API once per module/lesson, which can be slow or unreachable, and must not
    block the API from serving requests like GET /api/modules while it runs."""
    db = SessionLocal()
    try:
        rag_service.reset_vector_db()
        index_module_content(db)
    except Exception as e:
        print(f"Warning: content indexing skipped due to error: {e}")
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        track = db.query(models.Track).filter(models.Track.name == seed_data.TRACK_NAME).first()
        if not track:
            track = models.Track(name=seed_data.TRACK_NAME, description=seed_data.TRACK_DESCRIPTION)
            db.add(track)
            db.commit()
            db.refresh(track)

        for module_spec in seed_data.MODULES:
            _seed_module(db, track, module_spec)

        deduplicate_lessons(db)
    finally:
        db.close()

    threading.Thread(target=_index_content_in_background, daemon=True).start()

# Auth API
@app.post("/api/auth/register", response_model=schemas.UserOut, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.User)
        .filter(
            (models.User.username == user_in.username)
            | (models.User.email == user_in.email)
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token(subject=user.username)
    return schemas.Token(access_token=token)


@app.get("/api/auth/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/api/modules", response_model=List[schemas.Module])
def list_modules(db: Session = Depends(get_db)):
    return db.query(models.Module).order_by(models.Module.order).all()


@app.get("/api/modules/{module_id}", response_model=schemas.Module)
def read_module(module_id: int, db: Session = Depends(get_db)):
    db_module = db.query(models.Module).filter(models.Module.id == module_id).first()
    if db_module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return db_module

@app.get("/api/modules/title/{title}", response_model=schemas.Module)
def read_module_by_title(title: str, db: Session = Depends(get_db)):
    db_module = db.query(models.Module).filter(models.Module.title == title).first()
    if db_module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return db_module

# Progress API (FR-07 Progress Saving, FR-08 Resume Learning, FR-09 Progress Display)

def _get_or_create_user_progress(db: Session, user_id: int, module_id: int) -> models.UserProgress:
    row = (
        db.query(models.UserProgress)
        .filter(models.UserProgress.user_id == user_id, models.UserProgress.module_id == module_id)
        .first()
    )
    if row is None:
        row = models.UserProgress(
            user_id=user_id,
            module_id=module_id,
            status=models.ProgressStatus.IN_PROGRESS,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _build_module_progress(db: Session, user_id: int, module_id: int) -> schemas.ModuleProgressOut:
    module = db.query(models.Module).filter(models.Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")

    lesson_ids = [l.id for l in module.lessons]
    completed_ids = []
    if lesson_ids:
        completed_ids = [
            row.lesson_id
            for row in db.query(models.LessonProgress)
            .filter(
                models.LessonProgress.user_id == user_id,
                models.LessonProgress.lesson_id.in_(lesson_ids),
                models.LessonProgress.completed == True,  # noqa: E712
            )
            .all()
        ]

    progress = (
        db.query(models.UserProgress)
        .filter(models.UserProgress.user_id == user_id, models.UserProgress.module_id == module_id)
        .first()
    )
    status = progress.status if progress else models.ProgressStatus.LOCKED.value
    last_accessed = progress.last_accessed if progress else None
    percentage = round((len(completed_ids) / len(lesson_ids)) * 100) if lesson_ids else 0

    return schemas.ModuleProgressOut(
        module_id=module_id,
        status=status,
        completion_percentage=percentage,
        completed_lesson_ids=completed_ids,
        last_accessed=last_accessed,
    )


@app.post("/api/progress/modules/{module_id}/open", response_model=schemas.ModuleProgressOut)
def open_module(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Record that the learner opened a module, so it can be resumed later (FR-08)."""
    module = db.query(models.Module).filter(models.Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")

    row = _get_or_create_user_progress(db, current_user.id, module_id)
    row.last_accessed = datetime.now(timezone.utc)
    db.commit()

    return _build_module_progress(db, current_user.id, module_id)


@app.get("/api/progress/modules/{module_id}", response_model=schemas.ModuleProgressOut)
def get_module_progress(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _build_module_progress(db, current_user.id, module_id)


@app.put("/api/progress/lessons/{lesson_id}", response_model=schemas.ModuleProgressOut)
def set_lesson_completion(
    lesson_id: int,
    update: schemas.LessonCompletionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mark a lesson complete/incomplete for the logged-in user (FR-07)."""
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    row = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.user_id == current_user.id,
            models.LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = models.LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            completed=update.completed,
            completed_at=now if update.completed else None,
        )
        db.add(row)
    else:
        row.completed = update.completed
        row.completed_at = now if update.completed else None
    db.commit()

    module_id = lesson.module_id
    module_progress = _build_module_progress(db, current_user.id, module_id)

    user_progress = _get_or_create_user_progress(db, current_user.id, module_id)
    user_progress.status = (
        models.ProgressStatus.COMPLETED
        if module_progress.completion_percentage == 100
        else models.ProgressStatus.IN_PROGRESS
    )
    user_progress.last_accessed = now
    db.commit()

    return _build_module_progress(db, current_user.id, module_id)


@app.get("/api/progress", response_model=List[schemas.ModuleProgressOut])
def list_progress(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Progress for every module, for the logged-in user (FR-09 Progress Display)."""
    module_ids = [m.id for m in db.query(models.Module.id).order_by(models.Module.order).all()]
    return [_build_module_progress(db, current_user.id, module_id) for module_id in module_ids]


@app.get("/api/progress/resume", response_model=Optional[schemas.ResumeModuleOut])
def resume_last_module(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """The module the learner last accessed, for resume-on-login (FR-08)."""
    row = (
        db.query(models.UserProgress)
        .filter(models.UserProgress.user_id == current_user.id)
        .order_by(models.UserProgress.last_accessed.desc())
        .first()
    )
    if row is None:
        return None

    module = db.query(models.Module).filter(models.Module.id == row.module_id).first()
    if module is None:
        return None

    return schemas.ResumeModuleOut(
        module_id=module.id,
        module_title=module.title,
        status=row.status,
        last_accessed=row.last_accessed,
    )


# Chat API
class ChatContext(BaseModel):
    title: str
    id: int
    type: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[ChatContext] = None

def _resolve_module_id(db: Session, context: Optional[ChatContext]) -> Optional[int]:
    if context is None:
        return None
    if context.type == "module":
        return context.id
    if context.type == "lesson":
        lesson = db.query(models.Lesson).filter(models.Lesson.id == context.id).first()
        return lesson.module_id if lesson else None
    return None


@app.post("/api/chat")
def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    module_id = _resolve_module_id(db, request.context)
    try:
        response = rag_service.query_rag(request.message, request.context, module_id=module_id)
    except RAGNotConfiguredError as e:
        print(f"Chat unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail="The AI tutor is not configured yet. Set GOOGLE_API_KEY in backend/.env and restart the backend.",
        )
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # FR-10 Chat History Storage
    db.add(models.ChatMessage(user_id=current_user.id, module_id=module_id, role="user", content=request.message))
    db.add(models.ChatMessage(user_id=current_user.id, module_id=module_id, role="assistant", content=response["answer"]))
    db.commit()

    return response


@app.get("/api/chat/history", response_model=List[schemas.ChatHistorySummaryOut])
def list_chat_history_summaries(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """One entry per module the learner has chatted in, most recent first."""
    rows = (
        db.query(
            models.ChatMessage.module_id,
            models.Module.title,
            func.max(models.ChatMessage.timestamp).label("last_message_at"),
        )
        .join(models.Module, models.Module.id == models.ChatMessage.module_id)
        .filter(models.ChatMessage.user_id == current_user.id)
        .group_by(models.ChatMessage.module_id, models.Module.title)
        .order_by(func.max(models.ChatMessage.timestamp).desc())
        .all()
    )
    return [
        schemas.ChatHistorySummaryOut(module_id=r[0], module_title=r[1], last_message_at=r[2])
        for r in rows
    ]


@app.get("/api/chat/history/{module_id}", response_model=List[schemas.ChatMessageOut])
def get_chat_history(
    module_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Past chat messages for this learner in this module (FR-10)."""
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id, models.ChatMessage.module_id == module_id)
        .order_by(models.ChatMessage.timestamp.asc())
        .all()
    )
