import json
from pathlib import Path


INDEX_FILE = Path("index/chunks.json")


def load_chunks():
    with open(INDEX_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def check_all_documents(chunks):
    documents = set()

    for chunk in chunks:
        documents.add(chunk.get("doc"))

    if len(documents) == 7:
        print("PASS: all 7 documents are present")
        return True
    else:
        print(f"FAIL: expected 7 documents, found {len(documents)}")
        return False


def check_required_fields(chunks):
    required_fields = ["text", "doc", "page", "date"]

    for i, chunk in enumerate(chunks):
        for field in required_fields:
            if field not in chunk:
                print(f"FAIL: chunk {i} is missing field '{field}'")
                return False

        if not isinstance(chunk["text"], str) or not chunk["text"].strip():
            print(f"FAIL: chunk {i} has empty text")
            return False

    print("PASS: every chunk has text, doc, page and date")
    return True


def check_html_pages(chunks):
    for i, chunk in enumerate(chunks):
        doc = str(chunk.get("doc", "")).lower()

        if doc.endswith(".html") or doc.endswith(".htm"):
            if chunk.get("page") is not None:
                print(
                    f"FAIL: HTML chunk {i} has page={chunk.get('page')} "
                    f"instead of null"
                )
                return False

    print("PASS: HTML chunks have page as null")
    return True


def main():
    chunks = load_chunks()

    check_all_documents(chunks)
    check_required_fields(chunks)
    check_html_pages(chunks)


if __name__ == "__main__":
    main()