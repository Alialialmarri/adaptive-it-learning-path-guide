#!/usr/bin/env python
"""RAG evaluation harness for the AI tutor (uses the REAL Gemini API).

What it does
  1. Indexes the seeded course content into a separate ChromaDB folder using the
     same chunking (1000/100), embedding model and metadata as the application.
  2. Sends every question in rag_eval_dataset.json through RAGService.query_rag
     with the question's active module, exactly as /api/chat does.
  3. Records: retrieved passages, generated answer, relevance scores, whether the
     module filter leaked another module's text, and latency.
  4. Scores answered questions with three RAGAS-style metrics, using an LLM judge
     (temperature 0):
       - context_precision : share of the 3 retrieved passages that are relevant
                             to the question (precision@3)
       - faithfulness      : share of the answer's factual claims that are
                             supported by the retrieved passages
       - answer_relevancy  : judge score 1-5 of how well the answer addresses the
                             question compared with the reference answer, /5
  5. Writes results/rag_eval_results.json, rag_eval_results.csv and
     rag_eval_summary.md.

Usage (from the backend folder, with GOOGLE_API_KEY set in backend/.env):
    python tests/eval/run_rag_eval.py
    python tests/eval/run_rag_eval.py --limit 6        # quick smoke test
    python tests/eval/run_rag_eval.py --reuse-index    # skip re-embedding

Nothing in this file produces numbers by itself: every score in the report must
come from the output files of an actual run.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, BACKEND)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(BACKEND, ".env"))

REDIRECT_PREFIX = "That question looks like it's outside"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default=os.path.join(HERE, "rag_eval_dataset.json"))
    p.add_argument("--out", default=os.path.join(BACKEND, "tests", "results"))
    p.add_argument("--persist-dir", default=os.path.join(BACKEND, "eval_chroma"))
    p.add_argument("--reuse-index", action="store_true", help="do not rebuild the vector index")
    p.add_argument("--judge-model", default="gemini-3.6-flash")
    p.add_argument("--sleep", type=float, default=2.0, help="seconds between API calls (rate limits)")
    p.add_argument("--limit", type=int, default=0, help="only run the first N questions")
    p.add_argument("--retrieval-only", action="store_true",
                   help="no generation and no judging: runs retrieval, the relevance gate and the module filter only "
                        "(uses embeddings only, so it works when the generation quota is used up)")
    p.add_argument("--summary-only", action="store_true",
                   help="rewrite rag_eval_summary.md from the saved rag_eval_results.json without calling any API")
    p.add_argument("--metric", choices=["l2", "cosine"], default="l2",
                   help="distance metric of the Chroma collection: l2 (the application's default) or cosine. "
                        "Use a separate --persist-dir and --out for each metric.")
    p.add_argument("--grpc", action="store_true",
                   help="use the library's default gRPC transport instead of REST (REST is the default here "
                        "because gRPC calls timed out with 504 on the test machine)")
    p.add_argument("--one-judge", action="store_true",
                   help="score context precision, faithfulness and answer relevancy in ONE judge request per "
                        "question (same criteria as the separate judges), to fit the daily free-tier quota")
    p.add_argument("--resume", action="store_true",
                   help="keep questions already scored without error in rag_eval_results.json and run only the rest")
    return p.parse_args()


def text_of(response):
    content = response.content
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return content


def ask_json(judge, prompt, sleep, tries=3):
    last = None
    for attempt in range(tries):
        try:
            raw = text_of(judge.invoke(prompt))
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            return json.loads(match.group(0))
        except Exception as exc:  # network, quota, malformed JSON
            last = exc
            time.sleep(sleep * (attempt + 1))
    raise RuntimeError(f"judge failed after {tries} tries: {last}")


def build_index(svc, seed_data, sleep):
    svc.reset_vector_db()
    lesson_id = 0
    for module_id, module in enumerate(seed_data.MODULES, start=1):
        svc.ingest_text(
            f"Module: {module['title']}\nContent: {module['content']}",
            metadata={"type": "module", "id": module_id, "title": module["title"], "module_id": module_id},
        )
        time.sleep(sleep)
        for lesson in module["lessons"]:
            lesson_id += 1
            svc.ingest_text(
                f"Lesson: {lesson['title']} (Module: {module['title']})\nContent: {lesson['content']}",
                metadata={"type": "lesson", "id": lesson_id, "title": lesson["title"], "module_id": module_id},
            )
            time.sleep(sleep)


def judge_context_precision(judge, question, reference, passages, sleep):
    numbered = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages))
    prompt = (
        "You are grading a retrieval system. For each numbered passage decide whether it contains "
        "information that is useful for answering the question.\n"
        f"Question: {question}\nReference answer: {reference}\n\nPassages:\n{numbered}\n\n"
        'Reply with JSON only: {"relevant": [true, false, ...]} with one boolean per passage, in order.'
    )
    flags = ask_json(judge, prompt, sleep)["relevant"]
    flags = [bool(f) for f in flags][: len(passages)]
    return sum(flags) / len(passages) if passages else None


def judge_faithfulness(judge, answer, passages, sleep):
    context = "\n\n".join(passages)
    prompt = (
        "Break the ANSWER into its individual factual claims (ignore greetings and questions to the "
        "student). For each claim say whether it is directly supported by the CONTEXT.\n"
        f"CONTEXT:\n{context}\n\nANSWER:\n{answer}\n\n"
        'Reply with JSON only: {"claims": [{"claim": "...", "supported": true}]}'
    )
    claims = ask_json(judge, prompt, sleep)["claims"]
    if not claims:
        return None, []
    supported = sum(1 for c in claims if c.get("supported") is True)
    return supported / len(claims), claims


def judge_answer_relevancy(judge, question, answer, reference, sleep):
    prompt = (
        "Score how well the ANSWER addresses the QUESTION, using the REFERENCE answer as the gold "
        "standard. 5 = fully and correctly answers the question; 3 = partly answers or contains "
        "noticeable gaps; 1 = does not answer the question.\n"
        f"QUESTION: {question}\nREFERENCE: {reference}\nANSWER: {answer}\n\n"
        'Reply with JSON only: {"score": 1-5, "reason": "one sentence"}'
    )
    result = ask_json(judge, prompt, sleep)
    return float(result["score"]) / 5.0, result.get("reason", "")


def judge_all_in_one(judge, question, reference, answer, passages, sleep, with_relevancy=True):
    """The same three criteria as the separate judges, asked in a single request."""
    numbered = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(passages))
    prompt = (
        "You are grading one answer of a retrieval-augmented tutor. Do three tasks.\n"
        "Task 1 (context precision): for each numbered passage decide whether it contains information "
        "useful for answering the question.\n"
        "Task 2 (faithfulness): break the ANSWER into its individual factual claims (ignore greetings and "
        "questions to the student) and say for each claim whether it is directly supported by the passages.\n"
        "Task 3 (answer relevancy): score how well the ANSWER addresses the QUESTION, using the REFERENCE "
        "answer as the gold standard. 5 = fully and correctly answers; 3 = partly answers or has noticeable "
        "gaps; 1 = does not answer.\n\n"
        f"QUESTION: {question}\nREFERENCE: {reference}\n\nPASSAGES:\n{numbered}\n\nANSWER:\n{answer}\n\n"
        'Reply with JSON only: {"relevant": [true, false, ...], '
        '"claims": [{"claim": "...", "supported": true}], "score": 1-5, "reason": "one sentence"}'
    )
    r = ask_json(judge, prompt, sleep)
    flags = [bool(f) for f in r.get("relevant", [])][: len(passages)]
    cp = sum(flags) / len(passages) if passages else None
    claims = r.get("claims") or []
    faith = (sum(1 for c in claims if c.get("supported") is True) / len(claims)) if claims else None
    rel = float(r["score"]) / 5.0 if with_relevancy and r.get("score") is not None else None
    return cp, faith, claims, rel, (r.get("reason", "") if with_relevancy else None)


class _OneJudgeDone(Exception):
    pass


def pct(values):
    values = [v for v in values if v is not None]
    return round(100 * statistics.mean(values), 1) if values else None


def lat_stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    values = sorted(values)
    return {
        "n": len(values),
        "mean_s": round(statistics.mean(values), 2),
        "median_s": round(statistics.median(values), 2),
        "p95_s": round(values[int(0.95 * (len(values) - 1))], 2),
        "max_s": round(values[-1], 2),
    }


def save_partial(args, records):
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "rag_eval_results.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def main():
    args = parse_args()
    if args.retrieval_only and args.out == os.path.join(BACKEND, "tests", "results"):
        args.out = os.path.join(BACKEND, "tests", "results", "retrieval_only")  # keep separate from a full run
    if args.summary_only:
        saved = json.load(open(os.path.join(args.out, "rag_eval_results.json"), encoding="utf-8"))
        write_summary(args, saved, "unknown (not read in summary-only mode)")
        print(f"Summary rewritten in {args.out}")
        return
    if not os.getenv("GOOGLE_API_KEY"):
        sys.exit("GOOGLE_API_KEY is not set (put it in backend/.env). Nothing was evaluated.")

    from langchain_google_genai import ChatGoogleGenerativeAI

    from app import seed_data
    from app.services.rag_service import RAGService

    dataset = json.load(open(args.dataset, encoding="utf-8"))
    if args.limit:
        dataset = dataset[: args.limit]
    module_ids = {m["title"]: i for i, m in enumerate(seed_data.MODULES, start=1)}

    if args.metric != "l2":
        # Same code path, but every Chroma collection the service opens is created with the chosen metric.
        import functools
        import app.services.rag_service as rag_module_metric
        rag_module_metric.Chroma = functools.partial(
            rag_module_metric.Chroma, collection_metadata={"hnsw:space": args.metric})
        print(f"Distance metric: {args.metric}")
    if not args.grpc:
        # Same models and settings as the application; only the HTTP transport differs.
        import functools
        import app.services.rag_service as rag_module_rest
        rag_module_rest.ChatGoogleGenerativeAI = functools.partial(
            rag_module_rest.ChatGoogleGenerativeAI, transport="rest", timeout=300, max_retries=1)
        ChatGoogleGenerativeAI = functools.partial(ChatGoogleGenerativeAI, transport="rest", timeout=180)
    svc = RAGService(data_dir="./data", persist_dir=args.persist_dir)
    if args.retrieval_only:
        # Run the real query_rag code path, but stop right after the relevance gate:
        # a redirect is returned normally, and a question that passes the gate raises
        # _GatePassed instead of calling the Gemini model.
        import app.services.rag_service as rag_module

        class _GatePassed(Exception):
            pass

        def _stop_before_generation(*a, **k):
            raise _GatePassed()

        rag_module.RetrievalQA.from_chain_type = staticmethod(_stop_before_generation)
    if not args.reuse_index:
        print("Indexing course content (this calls the Gemini embeddings API)...")
        build_index(svc, seed_data, args.sleep)
    svc.get_retriever(None)  # attaches the persisted store
    chunk_count = svc.vector_db._collection.count()
    print(f"Vector store ready: {chunk_count} chunks")

    judge = ChatGoogleGenerativeAI(model=args.judge_model, temperature=0, max_retries=1)
    os.makedirs(args.out, exist_ok=True)
    results_path = os.path.join(args.out, "rag_eval_results.json")
    done = {}
    if args.resume and os.path.exists(results_path):
        for r in json.load(open(results_path, encoding="utf-8")):
            if not r.get("error"):
                done[r["id"]] = r
        print(f"Resuming: {len(done)} questions already complete, they will be kept.")
    records = []
    quota_stop = False
    for n, item in enumerate(dataset, start=1):
        if item["id"] in done:
            records.append(done[item["id"]])
            continue
        if quota_stop:
            break
        mid = module_ids[item["active_module"]]
        ctx = SimpleNamespace(type="module", id=mid, title=item["active_module"])
        rec = dict(item, active_module_id=mid, error=None)
        print(f"[{n}/{len(dataset)}] {item['id']} ({item['category']}) {item['question']}")

        # evidence about retrieval itself
        try:
            scored = svc.vector_db.similarity_search_with_relevance_scores(
                item["question"], k=3, filter={"module_id": mid}
            )
            rec["retrieved_candidates"] = [
                {"module_id": d.metadata.get("module_id"), "title": d.metadata.get("title"), "score": round(s, 3)}
                for d, s in scored
            ]
            rec["best_relevance_score"] = max((s for _, s in scored), default=0.0)
            rec["module_filter_leak"] = any(d.metadata.get("module_id") != mid for d, _ in scored)
            wanted = {t.strip() for t in item["source_lesson"].replace("Data Structures / ", "").replace("Python Programming / ", "").split(" / ")}
            rec["source_lesson_in_top3"] = any(d.metadata.get("title") in wanted for d, _ in scored)
            unfiltered = svc.vector_db.similarity_search_with_relevance_scores(item["question"], k=3)
            rec["unfiltered_top_module_id"] = unfiltered[0][0].metadata.get("module_id") if unfiltered else None
            rec["unfiltered_top_score"] = round(unfiltered[0][1], 3) if unfiltered else None
        except Exception as exc:
            rec["error"] = f"retrieval evidence failed: {exc}"
        time.sleep(args.sleep)

        # the actual tutor call, timed as /api/chat would experience it
        started = time.perf_counter()
        try:
            result = svc.query_rag(item["question"], ctx, module_id=mid)
            rec["latency_s"] = round(time.perf_counter() - started, 2)
            rec["answer"] = result["answer"]
            rec["retrieved_passages"] = result["source_documents"]
            rec["redirected"] = result["answer"].startswith(REDIRECT_PREFIX)
        except Exception as exc:
            if args.retrieval_only and type(exc).__name__ == "_GatePassed":
                # passed the relevance gate; generation was skipped on purpose
                rec["latency_s"] = None
                rec["answer"], rec["retrieved_passages"], rec["redirected"] = None, [], False
                time.sleep(args.sleep)
                rec.update(context_precision=None, faithfulness=None, answer_relevancy=None, relevancy_reason=None,
                           behaviour_ok=(item["category"] == "in_scope"))
                records.append(rec)
                save_partial(args, records)
                continue
            rec["latency_s"] = round(time.perf_counter() - started, 2)
            rec["error"] = f"{type(exc).__name__}: {exc}"
            rec["answer"], rec["retrieved_passages"], rec["redirected"] = None, [], None
        time.sleep(args.sleep)

        # behaviour outcome
        if rec["redirected"] is None:
            rec["behaviour_ok"] = None
        elif item["category"] == "in_scope":
            rec["behaviour_ok"] = not rec["redirected"]
        elif item["category"] == "out_of_scope":
            rec["behaviour_ok"] = rec["redirected"]
        else:  # insufficient information: redirecting is the desired outcome; answered ones are reviewed via faithfulness
            rec["behaviour_ok"] = rec["redirected"]

        # RAGAS-style scores for answered questions
        rec.update(context_precision=None, faithfulness=None, answer_relevancy=None, relevancy_reason=None)
        if rec["answer"] and not rec["redirected"] and item["category"] in ("in_scope", "insufficient_information"):
            try:
                reference = item["reference_answer"]
                if args.one_judge:
                    (rec["context_precision"], rec["faithfulness"], rec["claims"],
                     rec["answer_relevancy"], rec["relevancy_reason"]) = judge_all_in_one(
                        judge, item["question"], reference, rec["answer"], rec["retrieved_passages"],
                        args.sleep, with_relevancy=(item["category"] == "in_scope"))
                    time.sleep(args.sleep)
                    raise _OneJudgeDone()
                rec["context_precision"] = judge_context_precision(judge, item["question"], reference, rec["retrieved_passages"], args.sleep)
                time.sleep(args.sleep)
                rec["faithfulness"], rec["claims"] = judge_faithfulness(judge, rec["answer"], rec["retrieved_passages"], args.sleep)
                time.sleep(args.sleep)
                if item["category"] == "in_scope":
                    rec["answer_relevancy"], rec["relevancy_reason"] = judge_answer_relevancy(judge, item["question"], rec["answer"], reference, args.sleep)
                time.sleep(args.sleep)
            except _OneJudgeDone:
                pass
            except Exception as exc:
                rec["error"] = (rec["error"] or "") + f" scoring failed: {exc}"
        if "PerDay" in (rec["error"] or ""):
            quota_stop = True
            print("\nError returned by the API:\n" + (rec["error"] or "")[:1500])
            print("\nDaily API quota is used up. Stopping. Run the same command again after the quota resets "
                  "(or after enabling billing); with --resume the finished questions are kept.")
            # do not keep the question that hit the quota: it will be re-run
            save_partial(args, records)
            break
        records.append(rec)
        save_partial(args, records)

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    cols = ["id", "active_module", "category", "question", "redirected", "behaviour_ok", "best_relevance_score",
            "module_filter_leak", "source_lesson_in_top3", "unfiltered_top_module_id", "context_precision",
            "faithfulness", "answer_relevancy", "latency_s", "error"]
    with open(os.path.join(args.out, "rag_eval_results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    write_summary(args, records, chunk_count)
    print(f"\nDone. Results written to {args.out}")


def write_summary(args, records, chunk_count):
    by = lambda c: [r for r in records if r["category"] == c]
    ins, outs, insuf = by("in_scope"), by("out_of_scope"), by("insufficient_information")
    answered_in = [r for r in ins if r["redirected"] is False]
    lines = ["# RAG evaluation summary", "",
             f"- Questions run: {len(records)} (in-scope {len(ins)}, out-of-scope {len(outs)}, insufficient-information {len(insuf)})",
             f"- Vector store: {chunk_count} chunks; judge model: {args.judge_model} (temperature 0{', all three metrics in one request per question' if args.one_judge else ''}); answer model: {os.getenv('GEMINI_CHAT_MODEL', 'gemini-flash-lite-latest')}",
             f"- Questions with an execution error: {sum(1 for r in records if r['error'])}", "",
             "## In-scope questions",
             f"- Answered (not redirected): {len(answered_in)} / {len(ins)}; wrongly redirected: {sum(1 for r in ins if r['redirected'])}",
             f"- Correct source lesson in the top-3 retrieved chunks: {sum(1 for r in ins if r.get('source_lesson_in_top3'))} / {len(ins)}",
             f"- Context precision (mean): {pct(r['context_precision'] for r in ins)} %",
             f"- Faithfulness (mean): {pct(r['faithfulness'] for r in ins)} %",
             f"- Answer relevancy (mean): {pct(r['answer_relevancy'] for r in ins)} %", "",
             "## Out-of-scope questions",
             f"- Correctly redirected: {sum(1 for r in outs if r['behaviour_ok'])} / {len(outs)}", "",
             "## Insufficient-information questions",
             f"- Redirected: {sum(1 for r in insuf if r['redirected'])} / {len(insuf)}; answered anyway: {sum(1 for r in insuf if r['redirected'] is False)}",
             f"- Faithfulness of the answered ones (mean): {pct(r['faithfulness'] for r in insuf)} %", "",
             "## Module filter",
             f"- Questions where a retrieved chunk came from another module: {sum(1 for r in records if r.get('module_filter_leak'))} / {len(records)}", "",
             "## Latency of query_rag (seconds)",
             f"- Answered path: {lat_stats([r['latency_s'] for r in records if r['redirected'] is False])}",
             f"- Redirect path: {lat_stats([r['latency_s'] for r in records if r['redirected'] is True])}", ""]
    good = [r for r in answered_in if (r["faithfulness"] or 0) >= 0.8 and (r["answer_relevancy"] or 0) >= 0.8]
    bad = [r for r in ins if r["redirected"] or (r["answer_relevancy"] is not None and r["answer_relevancy"] < 0.6)
           or (r["faithfulness"] is not None and r["faithfulness"] < 0.6)]
    lines.append("## Candidate examples for the report")
    for title, group in (("Correct", good[:2]), ("Incorrect or weak", bad[:2] + [r for r in outs if not r["behaviour_ok"]][:1])):
        for r in group:
            lines += [f"### {title}: {r['id']} - {r['question']}",
                      f"- Active module: {r['active_module']}; redirected: {r['redirected']}; best score: {r.get('best_relevance_score')}",
                      f"- Scores: precision={r['context_precision']}, faithfulness={r['faithfulness']}, relevancy={r['answer_relevancy']}",
                      f"- Answer: {(r['answer'] or '')[:400]}", ""]
    with open(os.path.join(args.out, "rag_eval_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
