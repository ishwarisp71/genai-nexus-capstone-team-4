"""Score results.   python eval/evaluate.py <expected.json> <results.json> [--retrieval]

expected.json : list of {id, question, answer, sources, sql}  (same shape as the sample file)
results.json  : output of run_questions.py
--retrieval   : also compute Hit@5 and MRR of search() (no Gemini text calls)
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def kind(answer, sql):
    """Classify an expected answer: refuse, dont_know, sql or docs."""
    a = (answer or "").lower()
    if a.startswith("i can't do that") or a.startswith("i can’t do that"):
        return "refuse"
    if a.startswith("i don't know") or a.startswith("i don’t know"):
        return "dont_know"
    return "sql" if sql else "docs"


def got_kind(r):
    a = (r.get("answer") or "").lower()
    if a.startswith("i can't do that") or a.startswith("i can’t do that"):
        return "refuse"
    if r.get("dont_know"):
        return "dont_know"
    return "sql" if r.get("sql") else "docs"


def numbers(text):
    return set(re.findall(r"\d+(?:[.:]\d+)?", text or ""))


def retrieval_scores(expected):
    from helpdesk.search import search
    hits, rr, n = 0, 0.0, 0
    for e in expected:
        docs = {s["doc"] for s in e.get("sources", [])}
        if not docs:
            continue
        n += 1
        found = [r["doc"] for r in search(e["question"], k=5)]
        for rank, d in enumerate(found, 1):
            if d in docs:
                hits += 1
                rr += 1 / rank
                break
    return hits, rr, n


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    expected = {e["id"]: e for e in load(sys.argv[1])}
    results = {r["id"]: r for r in load(sys.argv[2])}

    ok_kind = ok_src = n_src = ok_fact = n_fact = 0
    print(f"{'ID':5} {'behaviour':10} {'sources':8} {'facts':6}")
    for qid, r in results.items():
        e = expected.get(qid)
        if not e:
            continue
        k_ok = kind(e["answer"], e.get("sql")) == got_kind(r)
        ok_kind += k_ok

        exp_docs = {s["doc"] for s in e.get("sources", [])}
        if exp_docs:
            n_src += 1
            got_docs = {s["doc"] for s in r.get("sources", [])}
            s_ok = bool(exp_docs & got_docs)
            ok_src += s_ok
            s_txt = "OK" if s_ok else "MISS"
        else:
            s_txt = "-"

        nums = numbers(e["answer"])
        if nums and kind(e["answer"], e.get("sql")) in ("docs", "sql"):
            n_fact += 1
            f_ok = bool(nums & numbers(r.get("answer")))
            ok_fact += f_ok
            f_txt = "OK" if f_ok else "MISS"
        else:
            f_txt = "-"
        print(f"{qid:5} {'OK' if k_ok else 'WRONG':10} {s_txt:8} {f_txt:6}")

    total = len(results)
    print(f"\nBehaviour (answer / don't know / refuse / sql): {ok_kind}/{total}")
    print(f"Right source document: {ok_src}/{n_src}")
    print(f"Rough fact check (a key number matches): {ok_fact}/{n_fact}  (check by eye too)")

    if "--retrieval" in sys.argv:
        hits, rr, n = retrieval_scores(list(expected.values()))
        if n:
            print(f"Retrieval Hit@5: {hits}/{n} = {hits / n:.2f}   MRR: {rr / n:.2f}")


if __name__ == "__main__":
    main()