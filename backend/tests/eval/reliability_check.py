#!/usr/bin/env python
"""Reliability check: what happens when the Gemini API call fails?

Run 1 (invalid key):   python tests/eval/reliability_check.py
Run 2 (no network):    disconnect from the internet, then run the same command.

It reports the exception type, the message (truncated) and how long the failure
took, for both indexing and answering. The backend is considered to handle the
failure if /api/chat returns an error response instead of crashing; that
behaviour is asserted separately in tests/test_api_functional.py
(test_chat_without_api_key_returns_503_not_a_crash and
test_chat_internal_error_returns_500_and_stores_nothing).
"""
import os
import sys
import tempfile
import time
from types import SimpleNamespace

BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, BACKEND)

os.environ["GOOGLE_API_KEY"] = "invalid-key-for-reliability-test"

from app.services.rag_service import RAGService  # noqa: E402

svc = RAGService(data_dir="./data", persist_dir=tempfile.mkdtemp(prefix="rel_chroma_"))
for label, call in (
    ("index a chunk", lambda: svc.ingest_text("Stacks are LIFO.", metadata={"module_id": 1, "title": "Stacks"})),
    ("answer a question", lambda: svc.query_rag("What is a stack?", SimpleNamespace(type="module", id=1, title="Data Structures"), module_id=1)),
):
    start = time.perf_counter()
    try:
        call()
        print(f"{label}: unexpectedly succeeded")
    except Exception as exc:
        print(f"{label}: failed after {time.perf_counter() - start:.1f}s with {type(exc).__name__}: {str(exc)[:200]}")
