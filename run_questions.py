"""Run many questions:  python run_questions.py <questions.json> <results.json>
Optional third argument: how many questions to run (for quick tests)."""
import json
import sys
import time

from helpdesk.pipeline import ask


def load_questions(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("questions", "items", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    items = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            items.append({"id": f"Q{i + 1:02d}", "question": item})
        else:
            q = item.get("question") or item.get("q") or item.get("text") or ""
            items.append({"id": item.get("id", f"Q{i + 1:02d}"), "question": q})
    return items


def main():
    if len(sys.argv) < 3:
        print("Usage: python run_questions.py <questions.json> <results.json> [limit]")
        sys.exit(1)
    items = load_questions(sys.argv[1])
    if len(sys.argv) > 3:
        items = items[: int(sys.argv[3])]

    results = []
    for n, item in enumerate(items, 1):
        print(f"[{n}/{len(items)}] {item['id']}: {item['question'][:70]}")
        out = ask(item["question"])
        results.append({"id": item["id"], "question": item["question"], **out})
        # Save after every question, so a crash never loses finished answers.
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        time.sleep(1)
    print(f"Done. Saved {len(results)} results to {sys.argv[2]}")


if __name__ == "__main__":
    main()