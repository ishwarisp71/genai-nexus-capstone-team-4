"""Write the final answer from document chunks and/or SQL rows."""
import json
import re

from helpdesk.llm import generate

DONT_KNOW_TEXT = "I don't know. The documents and database I have do not cover this."


def _extract_json(text):
    """Pull the first JSON object out of the model reply."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None


def _format_chunks(chunks):
    parts = []
    for i, c in enumerate(chunks):
        page = c["page"] if c["page"] is not None else "none (HTML file)"
        parts.append(
            f"[Chunk {i}] doc: {c['doc']} | page: {page} | date: {c['date']}\n{c['text']}"
        )
    return "\n\n".join(parts)


def _format_rows(sql_result):
    if not sql_result:
        return ""
    if sql_result.get("error"):
        return f"SQL query: {sql_result.get('sql')}\nSQL error: {sql_result['error']}"
    rows = sql_result.get("rows", [])
    return f"SQL query: {sql_result.get('sql')}\nRows returned ({len(rows)}):\n" + \
        json.dumps(rows, ensure_ascii=False, default=str)


def make_answer(question, chunks=None, sql_result=None):
    """Returns {"answer", "sources", "dont_know"}."""
    chunks = chunks or []
    has_docs = bool(chunks)
    has_sql = bool(sql_result and sql_result.get("sql"))

    if not has_docs and not has_sql:
        return {"answer": DONT_KNOW_TEXT, "sources": [], "dont_know": True}

    context = ""
    if has_docs:
        context += "DOCUMENT CHUNKS:\n" + _format_chunks(chunks) + "\n\n"
    if sql_result:
        context += "DATABASE RESULT (a 2016 timetable snapshot):\n" + _format_rows(sql_result) + "\n\n"

    prompt = f"""You are a help desk for Indian railway passengers.
Answer the QUESTION using ONLY the CONTEXT below. Do not use any other knowledge.

RULES:
- Write the answer in plain, simple words for a normal passenger.
- If two documents disagree, trust the one with the NEWEST date and ignore the older rule.
  Say briefly that the older rule has been replaced.
- If the context does not contain the answer (for example fares, seat availability,
  whether a waitlisted ticket will be confirmed, live train status), set
  "dont_know" to true and say that you do not know.
- Never guess and never invent numbers, train names or rules.
- Database results come from a 2016 timetable. Mention that the times may have
  changed since then.
- In "used_chunks" list ONLY the numbers of the chunks you really used.
  Use an empty list if you used no chunk.

Reply with ONLY a JSON object, no markdown, in this exact shape:
{{"answer": "...", "dont_know": false, "used_chunks": [0, 1]}}

CONTEXT:
{context}
QUESTION: {question}
"""
    try:
        data = _extract_json(generate(prompt))
    except Exception:
        data = None

    if not data or "answer" not in data:
        return {"answer": DONT_KNOW_TEXT, "sources": [], "dont_know": True}

    dont_know = bool(data.get("dont_know", False))

    sources = []
    seen = set()
    if not dont_know:
        for idx in data.get("used_chunks", []):
            try:
                c = chunks[int(idx)]
            except Exception:
                continue
            key = (c["doc"], c["page"])
            if key not in seen:
                seen.add(key)
                sources.append({"doc": c["doc"], "page": c["page"]})

    return {"answer": str(data["answer"]), "sources": sources, "dont_know": dont_know}