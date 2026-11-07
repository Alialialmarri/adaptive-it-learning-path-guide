"""Functional, security, persistence and isolation tests.

Test IDs (T-xx) match Table "Functional Test Cases" in Chapter 9 of the report.
Run:  cd backend && pytest tests/test_api_functional.py -v

Where the real AI model would be needed, `rag_service.query_rag` is replaced by
a stub so that the test verifies the backend behaviour around it (routing,
module scoping, storage), not the quality of the AI answer.
"""
import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

PY = "Python Programming"
DS = "Data Structures"


# ---------------------------------------------------------------- T-01 login
def test_T01_register_login_and_credential_validation(client):
    r = client.post(
        "/api/auth/register",
        json={"username": "login_user", "email": "login_user@example.com", "password": "Passw0rd-for-tests"},
    )
    assert r.status_code == 201
    assert "password" not in r.json() and "hashed_password" not in r.json()

    ok = client.post("/api/auth/login", json={"username": "login_user", "password": "Passw0rd-for-tests"})
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer" and ok.json()["access_token"]

    wrong = client.post("/api/auth/login", json={"username": "login_user", "password": "wrong"})
    assert wrong.status_code == 401
    unknown = client.post("/api/auth/login", json={"username": "nobody_here", "password": "x"})
    assert unknown.status_code == 401

    duplicate = client.post(
        "/api/auth/register",
        json={"username": "login_user", "email": "other@example.com", "password": "Passw0rd-for-tests"},
    )
    assert duplicate.status_code == 400
    bad_email = client.post(
        "/api/auth/register", json={"username": "x_user", "email": "not-an-email", "password": "p"}
    )
    assert bad_email.status_code == 422


def test_T01_me_endpoint_returns_logged_in_user(alice):
    r = alice.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == alice.username


# ----------------------------------------------------- T-02 / T-03 modules
def test_T02_modules_are_listed_in_order(modules, alice):
    data = alice.get("/api/modules").json()
    assert [m["title"] for m in data] == [PY, DS]
    assert len(modules[PY]["lessons"]) == 11
    assert len(modules[DS]["lessons"]) == 10


def test_T03_module_content_loads_with_lessons(alice, modules):
    r = alice.get(f"/api/modules/title/{DS}")
    assert r.status_code == 200
    lessons = sorted(r.json()["lessons"], key=lambda l: l["order"])
    assert lessons[0]["title"] == "Course Introduction"
    assert all(l["content"].strip() for l in lessons)
    by_id = alice.get(f"/api/modules/{modules[DS]['id']}")
    assert by_id.status_code == 200 and by_id.json()["title"] == DS
    assert alice.get("/api/modules/999999").status_code == 404
    assert alice.get("/api/modules/title/Does Not Exist").status_code == 404


# ------------------------------------------------------ T-04 / T-05 / T-10
@pytest.fixture()
def stub_ai(app_module, monkeypatch):
    calls = []

    def fake_query(query, context=None, module_id=None):
        calls.append({"query": query, "module_id": module_id})
        return {"answer": f"STUB ANSWER for: {query}", "source_documents": ["stub chunk"]}

    monkeypatch.setattr(app_module.rag_service, "query_rag", fake_query)
    return calls


def test_T04_chat_requires_authentication(client):
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 401


def test_T04_chat_returns_answer_and_sources(alice, modules, stub_ai):
    ctx = {"title": DS, "id": modules[DS]["id"], "type": "module"}
    r = alice.post("/api/chat", json={"message": "what is hash", "context": ctx})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].startswith("STUB ANSWER")
    assert isinstance(body["source_documents"], list)


def test_T05_active_module_is_passed_to_retrieval(alice, modules, stub_ai, db_session_factory):
    """The module id sent to the RAG service (which applies the Chroma filter
    {"module_id": id}) must follow the active module / lesson context."""
    ds_id, py_id = modules[DS]["id"], modules[PY]["id"]
    alice.post("/api/chat", json={"message": "q1", "context": {"title": DS, "id": ds_id, "type": "module"}})
    alice.post("/api/chat", json={"message": "q2", "context": {"title": PY, "id": py_id, "type": "module"}})
    lesson_id = modules[DS]["lessons"][0]["id"]
    alice.post("/api/chat", json={"message": "q3", "context": {"title": "L", "id": lesson_id, "type": "lesson"}})
    alice.post("/api/chat", json={"message": "q4"})
    assert [c["module_id"] for c in stub_ai] == [ds_id, py_id, ds_id, None]


def test_T05_T06_scope_gate_and_module_filter_unit(app_module, monkeypatch):
    """Unit test of RAGService.query_rag with a fake vector store (no Gemini).
    Verifies (a) retrieval is filtered by module_id with k=3, (b) a best relevance
    score below the relevance threshold (RAGService.MODULE_SCOPE_RELEVANCE_THRESHOLD)
    produces the redirect message with no source documents and no LLM call, (c) a score
    above the threshold passes the gate. The threshold is read from the class, so the
    test follows the value used by the application."""
    from types import SimpleNamespace

    from app.services.rag_service import RAGNotConfiguredError, RAGService

    seen = {}

    class FakeDB:
        def __init__(self, scores):
            self.scores = scores

        def as_retriever(self, search_kwargs=None):
            seen["search_kwargs"] = search_kwargs
            return object()

        def similarity_search_with_relevance_scores(self, query, k, filter):
            seen["scored_filter"], seen["k"] = filter, k
            return [(object(), s) for s in self.scores]

    svc = RAGService(data_dir="./data", persist_dir="./unit_chroma")
    ctx = SimpleNamespace(type="module", id=2, title=DS)

    svc.vector_db = FakeDB([0.31, 0.28, 0.2])
    low = svc.query_rag("Who won the World Cup?", context=ctx, module_id=2)
    assert low["source_documents"] == []
    assert "outside" in low["answer"]
    assert seen["search_kwargs"] == {"k": 3, "filter": {"module_id": 2}}
    assert seen["scored_filter"] == {"module_id": 2} and seen["k"] == 3

    passing = RAGService.MODULE_SCOPE_RELEVANCE_THRESHOLD + 0.05
    svc.vector_db = FakeDB([passing, 0.4, 0.3])
    with pytest.raises(RAGNotConfiguredError):  # passed the gate, reached the LLM, no key configured
        svc.query_rag("What is a stack?", context=ctx, module_id=2)


def test_T10_chat_is_stored_per_user_and_module(alice, modules, stub_ai, db_session_factory):
    ds_id = modules[DS]["id"]
    ctx = {"title": DS, "id": ds_id, "type": "module"}
    alice.post("/api/chat", json={"message": "stored question", "context": ctx})

    history = alice.get(f"/api/chat/history/{ds_id}").json()
    roles = [m["role"] for m in history]
    assert roles[-2:] == ["user", "assistant"]
    assert history[-2]["content"] == "stored question"

    summary = alice.get("/api/chat/history").json()
    assert any(s["module_id"] == ds_id and s["module_title"] == DS for s in summary)

    from app.models import models

    db = db_session_factory()
    try:
        rows = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.user_id == alice.user_id, models.ChatMessage.module_id == ds_id)
            .all()
        )
        assert len(rows) >= 2
    finally:
        db.close()


# -------------------------------------------------- T-07 / T-08 / T-09
def test_T09_new_learner_sees_zero_progress(client, modules):
    from conftest import Learner

    fresh = Learner(client, "fresh_test")
    r = fresh.get("/api/progress")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert all(i["completion_percentage"] == 0 and i["completed_lesson_ids"] == [] for i in items)
    assert fresh.get("/api/progress/resume").json() is None


def test_T07_progress_is_saved_and_module_completes(client, modules):
    from conftest import Learner

    carol = Learner(client, "carol_test")
    mod = modules[PY]
    lessons = sorted(mod["lessons"], key=lambda l: l["order"])

    opened = carol.post(f"/api/progress/modules/{mod['id']}/open")
    assert opened.status_code == 200 and opened.json()["status"] == "in_progress"

    first = carol.put(f"/api/progress/lessons/{lessons[0]['id']}", json={"completed": True}).json()
    assert first["completed_lesson_ids"] == [lessons[0]["id"]]
    assert first["completion_percentage"] == round(100 / len(lessons))
    assert first["status"] == "in_progress"

    for lesson in lessons[1:]:
        last = carol.put(f"/api/progress/lessons/{lesson['id']}", json={"completed": True}).json()
    assert last["completion_percentage"] == 100 and last["status"] == "completed"

    undone = carol.put(f"/api/progress/lessons/{lessons[0]['id']}", json={"completed": False}).json()
    assert undone["status"] == "in_progress" and lessons[0]["id"] not in undone["completed_lesson_ids"]

    assert carol.put("/api/progress/lessons/999999", json={"completed": True}).status_code == 404


def test_T08_resume_returns_last_accessed_module_after_relogin(client, modules):
    from conftest import Learner

    dave = Learner(client, "dave_test")
    dave.post(f"/api/progress/modules/{modules[PY]['id']}/open")
    time.sleep(0.05)
    dave.post(f"/api/progress/modules/{modules[DS]['id']}/open")
    lesson = modules[DS]["lessons"][0]["id"]
    dave.put(f"/api/progress/lessons/{lesson}", json={"completed": True})

    dave.login()  # simulate logout and a later login: a brand-new token

    resume = dave.get("/api/progress/resume").json()
    assert resume["module_title"] == DS
    progress = {p["module_id"]: p for p in dave.get("/api/progress").json()}
    assert lesson in progress[modules[DS]["id"]]["completed_lesson_ids"]


# -------------------------------------------------- diagnostic assessment
def test_T11_diagnostic_scores_and_recommends(client, modules, db_session_factory):
    import json

    from app.models import models
    from conftest import Learner

    erin = Learner(client, "erin_test")
    track_id = 1
    started = erin.post(f"/api/tracks/{track_id}/diagnostic/start")
    assert started.status_code == 200
    questions = started.json()["questions"]
    assert len(questions) == 15

    db = db_session_factory()
    try:
        correct = {q.id: json.loads(q.correct_choices) for q in db.query(models.DiagnosticQuestion).all()}
    finally:
        db.close()
    answers = [{"question_id": q["id"], "selected_choices": correct[q["id"]]} for q in questions]
    result = erin.post(f"/api/diagnostic/attempts/{started.json()['attempt_id']}/submit", json={"answers": answers})
    assert result.status_code == 200
    body = result.json()
    assert all(t["band"] == "mastered" and t["score"] == 100 for t in body["topic_mastery"])
    assert len(body["auto_completed_lesson_ids"]) == 5
    assert body["recommended_start_lesson_title"] == "Core Data Structures: Lists, Tuples, Dicts, Sets"


# ------------------------------------------------ isolation (privacy)
def test_isolation_between_users(client, alice, bob, modules, stub_ai):
    ds_id = modules[DS]["id"]
    alice.post("/api/chat", json={"message": "alice private question", "context": {"title": DS, "id": ds_id, "type": "module"}})
    alice.put(f"/api/progress/lessons/{modules[DS]['lessons'][0]['id']}", json={"completed": True})

    assert bob.get(f"/api/chat/history/{ds_id}").json() == []
    assert bob.get("/api/chat/history").json() == []
    bob_progress = {p["module_id"]: p for p in bob.get("/api/progress").json()}
    assert bob_progress[ds_id]["completed_lesson_ids"] == []
    assert bob.get("/api/progress/resume").json() is None

    started = alice.post("/api/tracks/1/diagnostic/start")
    attempt_id = started.json()["attempt_id"]
    stolen = bob.post(f"/api/diagnostic/attempts/{attempt_id}/submit", json={"answers": []})
    assert stolen.status_code == 403


# ------------------------------------------------------------ security
PROTECTED = [
    ("get", "/api/auth/me"),
    ("get", "/api/progress"),
    ("get", "/api/progress/resume"),
    ("get", "/api/progress/modules/1"),
    ("post", "/api/progress/modules/1/open"),
    ("get", "/api/chat/history"),
    ("get", "/api/chat/history/1"),
    ("post", "/api/tracks/1/diagnostic/start"),
    ("get", "/api/tracks/1/mastery"),
    ("get", "/api/modules"),
    ("get", "/api/modules/1"),
    ("get", "/api/modules/title/Python Programming"),
]


@pytest.mark.parametrize("method,url", PROTECTED)
def test_protected_endpoints_reject_missing_and_tampered_tokens(client, method, url):
    assert getattr(client, method)(url).status_code == 401
    assert getattr(client, method)(url, headers={"Authorization": "Bearer not.a.token"}).status_code == 401


def test_expired_token_is_rejected(client, alice):
    from conftest import TEST_JWT_SECRET

    expired = jwt.encode(
        {"sub": alice.username, "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    forged = jwt.encode(
        {"sub": alice.username, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "a-different-secret",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_password_is_stored_hashed(db_session_factory, alice):
    from app.models import models

    db = db_session_factory()
    try:
        user = db.query(models.User).filter(models.User.username == alice.username).one()
        assert user.hashed_password != alice.password
        assert user.hashed_password.startswith("$2")  # bcrypt
    finally:
        db.close()


def test_module_endpoints_require_authentication(client, alice):
    """The module endpoints were open before the security review; they now need a token."""
    for url in ["/api/modules", "/api/modules/1", "/api/modules/title/Python Programming"]:
        assert client.get(url).status_code == 401
        assert alice.get(url).status_code == 200


# ------------------------------------------------------ error handling
def test_chat_without_api_key_returns_503_not_a_crash(alice, modules):
    ctx = {"title": DS, "id": modules[DS]["id"], "type": "module"}
    r = alice.post("/api/chat", json={"message": "what is a stack", "context": ctx})
    assert r.status_code == 503
    assert "GOOGLE_API_KEY" in r.json()["detail"]
    assert alice.get("/api/progress").status_code == 200  # the rest of the app keeps working


def test_chat_internal_error_returns_500_and_stores_nothing(app_module, alice, modules, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("simulated upstream failure")

    monkeypatch.setattr(app_module.rag_service, "query_rag", boom)
    ds_id = modules[DS]["id"]
    before = len(alice.get(f"/api/chat/history/{ds_id}").json())
    r = alice.post("/api/chat", json={"message": "will fail", "context": {"title": DS, "id": ds_id, "type": "module"}})
    assert r.status_code == 500
    # The internal error text must not reach the client; it is logged on the server only.
    assert "simulated upstream failure" not in r.text
    assert r.json()["detail"] == "The AI tutor could not answer right now. Please try again later."
    after = len(alice.get(f"/api/chat/history/{ds_id}").json())
    assert after == before  # a failed request leaves no half-written chat rows
