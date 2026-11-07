#!/usr/bin/env python
"""Compare two retrieval-only runs (L2 and cosine) of run_rag_eval.py.

Usage: python tests/eval/compare_metrics.py tests/results_l2 tests/results_cosine
Writes tests/results/metric_comparison.md and prints it.
"""
import json, os, statistics, sys

def load(d):
    return json.load(open(os.path.join(d, "rag_eval_results.json"), encoding="utf-8"))

def wanted(r):
    s = r["source_lesson"].replace("Data Structures / ", "").replace("Python Programming / ", "")
    return {t.strip() for t in s.split(" / ")}

def stats(recs, name):
    ins = [r for r in recs if r["category"] == "in_scope"]
    outs = [r for r in recs if r["category"] == "out_of_scope"]
    insuf = [r for r in recs if r["category"] == "insufficient_information"]
    top1 = sum(1 for r in ins if r.get("retrieved_candidates") and r["retrieved_candidates"][0]["title"] in wanted(r))
    top3 = sum(1 for r in ins if r.get("source_lesson_in_top3"))
    leaks = sum(1 for r in recs if r.get("module_filter_leak"))
    sc = lambda g: [r["best_relevance_score"] for r in g if r.get("best_relevance_score") is not None]
    rng = lambda v: f"{min(v):.3f} to {max(v):.3f} (mean {statistics.mean(v):.3f})" if v else "n/a"
    # best single threshold separating in-scope (pass) from out-of-scope (redirect)
    cands = sorted(set(sc(ins) + sc(outs)))
    best_t, best_ok = None, -1
    for t in cands + [max(cands) + 1e-6] if cands else []:
        ok = sum(1 for v in sc(ins) if v >= t) + sum(1 for v in sc(outs) if v < t)
        if ok > best_ok:
            best_t, best_ok = t, ok
    if sc(ins) and sc(outs) and min(sc(ins)) > max(sc(outs)):
        best_t = (min(sc(ins)) + max(sc(outs))) / 2  # middle of the gap when the two groups separate fully
    gate = sum(1 for r in ins + outs if r.get("behaviour_ok"))
    margin = (min(sc(ins)) - max(sc(outs))) if sc(ins) and sc(outs) else None
    return {
        "name": name, "n_in": len(ins), "top1": top1, "top3": top3, "leaks": leaks, "n": len(recs),
        "in": rng(sc(ins)), "out": rng(sc(outs)), "insuf": rng(sc(insuf)),
        "gate070": f"{gate}/{len(ins) + len(outs)}",
        "best_t": f"{best_t:.3f}" if best_t is not None else "n/a",
        "best_ok": f"{best_ok}/{len(sc(ins)) + len(sc(outs))}",
        "margin": f"{margin:.3f}" if margin is not None else "n/a",
    }

a, b = stats(load(sys.argv[1]), "L2 (default)"), stats(load(sys.argv[2]), "Cosine")
rows = [("Correct lesson ranked first (in-scope)", "top1", "n_in"), ("Correct lesson in top 3 (in-scope)", "top3", "n_in"),
        ("Module filter leaks", "leaks", "n"), ("Best score, in-scope", "in", None), ("Best score, out-of-scope", "out", None),
        ("Best score, insufficient information", "insuf", None), ("Gap between lowest in-scope and highest out-of-scope", "margin", None),
        ("Gate correct at threshold 0.70", "gate070", None), ("Threshold that best separates in-scope from out-of-scope", "best_t", None),
        ("Gate correct at that threshold", "best_ok", None)]
out = ["# L2 vs cosine (retrieval only, same 36 questions)", "", f"| Measure | {a['name']} | {b['name']} |", "|---|---|---|"]
for label, k, tot in rows:
    f = lambda x: f"{x[k]}/{x[tot]}" if tot else str(x[k])
    out.append(f"| {label} | {f(a)} | {f(b)} |")
text = "\n".join(out) + "\n"
os.makedirs("tests/results", exist_ok=True)
open("tests/results/metric_comparison.md", "w", encoding="utf-8").write(text)
print(text)
