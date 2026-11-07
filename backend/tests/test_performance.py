"""Response-time measurement for the endpoints that do not call Gemini.

The measurements are taken in-process with FastAPI's TestClient, so they exclude
real network latency and browser rendering. They show backend + SQLite cost only.
AI answer latency (retrieval + Gemini) is measured by tests/eval/run_rag_eval.py.

Output: tests/results/performance_api.json  (also printed with `pytest -s`).
"""
import json
import os
import statistics
import time

N = 50
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _measure(call, n=N):
    samples = []
    for _ in range(n):
        start = time.perf_counter()
        response = call()
        samples.append((time.perf_counter() - start) * 1000)
        assert response.status_code == 200
    samples.sort()
    return {
        "requests": n,
        "mean_ms": round(statistics.mean(samples), 2),
        "median_ms": round(statistics.median(samples), 2),
        "p95_ms": round(samples[int(0.95 * (n - 1))], 2),
        "max_ms": round(samples[-1], 2),
    }


def test_backend_response_time_without_ai(client, alice, modules):
    mod_id = modules["Data Structures"]["id"]
    report = {
        "GET /api/modules": _measure(lambda: client.get("/api/modules")),
        "GET /api/auth/me": _measure(lambda: alice.get("/api/auth/me")),
        "GET /api/progress": _measure(lambda: alice.get("/api/progress")),
        "GET /api/progress/modules/{id}": _measure(lambda: alice.get(f"/api/progress/modules/{mod_id}")),
        "GET /api/chat/history/{id}": _measure(lambda: alice.get(f"/api/chat/history/{mod_id}")),
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "performance_api.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    assert all(v["mean_ms"] < 1000 for v in report.values())
