# Test kit for Chapter 9 (Testing and Validation)

Copy the contents of this folder into the project's `backend/` directory (same layout), then run everything **from `backend/`**.

```bash
pip install -r requirements-dev.txt
mkdir -p tests/results
```

| # | Command | Needs Gemini key? | Produces |
|---|---|---|---|
| 1 | `pytest tests/test_api_functional.py -v 2>&1 \| tee tests/results/functional_test_output.txt` | No | Pass/fail for T-01..T-11, security, isolation, persistence, error handling |
| 2 | `pytest tests/test_performance.py -s 2>&1 \| tee tests/results/performance_output.txt` | No | `tests/results/performance_api.json` (backend response time, no AI) |
| 3 | `python tests/eval/run_rag_eval.py` | **Yes** (`GOOGLE_API_KEY` in `backend/.env`) | `rag_eval_results.json/.csv`, `rag_eval_summary.md` (retrieval, module restriction, faithfulness, answer relevancy, context precision, AI latency) |
| 4 | `python tests/eval/reliability_check.py` (run once online, once with the network disconnected) | Not needed | Behaviour when the Gemini call fails |
| 5 | `python tests/db_validation.py sql_app.db > tests/results/db_validation.txt` | No | Row counts, referential integrity, ownership checks, hashed passwords, chunk counts |
| 6 | `pytest tests/test_diagnostic_service.py -v` (already in the repo) | No | Unit tests of mastery classification |

Notes
* Tests 1 and 2 use a temporary database; they never touch `sql_app.db`, `chroma_db/` or `.env`, and they never call Gemini (where an AI answer is needed the test says that it uses a stub).
* Test 3 spends Gemini quota (about 36 questions, each with several API calls). Use `--limit 6` first.
* Run test 5 after you have used the real application for a while (register 2 users, study, chat), so the database contains real records. Keep the terminal output as evidence; it never prints password hashes or e-mails.
* Take the screenshots listed in Section 9.7 of the report while the real application is running.
* Nothing in these scripts invents results. Copy the numbers into the report only from the files in `tests/results/`.
