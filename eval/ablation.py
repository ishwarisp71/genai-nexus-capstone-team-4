"""Measure search settings.  python eval/ablation.py data/questions/sample_questions.json
Uses only embedding calls (one per question), no text-generation calls."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from helpdesk.search import search

OLD_DOC = "indianrail_refund_rules_2015.html"
CONFLICT_Q = "cancellation charge confirmed ticket 12 hours before departure"

SETTINGS = [
    ("1 keyword only (BM25)", dict(use_embeddings=False, recency_weight=0)),
    ("2 + meaning search (hybrid)", dict(use_embeddings=True, recency_weight=0)),
    ("3 + recency boost (full system)", dict(use_embeddings=True, recency_weight=0.10)),
]

questions = [q for q in json.load(open(sys.argv[1], encoding="utf-8")) if q.get("sources")]
print(f"{len(questions)} document questions\n")
print(f"{'setting':34} {'Hit@5':>7} {'MRR':>6}  2015 file in top 5 for conflict question?")
for name, opts in SETTINGS:
    hits, rr = 0, 0.0
    for q in questions:
        want = {s["doc"] for s in q["sources"]}
        for rank, r in enumerate(search(q["question"], k=5, **opts), 1):
            if r["doc"] in want:
                hits += 1
                rr += 1 / rank
                break
    n = len(questions)
    old = any(r["doc"] == OLD_DOC for r in search(CONFLICT_Q, k=5, **opts))
    print(f"{name:34} {hits}/{n:<4} {rr / n:6.2f}  {'YES (bad)' if old else 'no (good)'}")