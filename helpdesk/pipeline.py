"""ask(question): route the question, call search and/or SQL, write the answer."""
from helpdesk.answer import make_answer, DONT_KNOW_TEXT
from helpdesk.llm import generate
from helpdesk.search import search
from helpdesk.sql import run_sql

REFUSAL_TEXT = "I can't do that. I only run read-only queries."


def _result(answer, sources=None, sql=None, dont_know=False):
    return {
        "answer": answer,
        "sources": sources or [],
        "sql": sql,
        "dont_know": dont_know,
    }


def _unknown():
    return _result(DONT_KNOW_TEXT, dont_know=True)


def _refusal():
    return _result(REFUSAL_TEXT)


def classify(question):
    """Returns DOCUMENTS, DATABASE, BOTH or REFUSE."""
    prompt = f"""You route questions for a railway help desk. Reply with ONE word only.

DOCUMENTS = about rules, refunds, cancellation charges, Tatkal, advance
            reservation period, circulars, gazette notifications, fares, or
            anything written in rule documents.
DATABASE  = about the 2016 timetable: train numbers, train names, stations,
            departure or arrival times, which trains go from A to B, counts
            of trains.
BOTH      = needs the timetable AND the rules together
            (for example a train's departure time plus the cancellation charge).
REFUSE    = asks to change, add, delete or damage any data, or to run anything
            other than reading.

QUESTION: {question}

ONE WORD:"""
    try:
        text = generate(prompt).strip().upper()
    except Exception:
        return "BOTH"
    for label in ("REFUSE", "BOTH", "DATABASE", "DOCUMENTS"):
        if label in text:
            return label
    return "BOTH"


def _ask(question):
    question = (question or "").strip()
    if not question:
        return _unknown()

    route = classify(question)

    if route == "REFUSE":
        return _refusal()

    if route == "DATABASE":
        sql_result = run_sql(question)
        if sql_result["refused"]:
            return _refusal()
        if sql_result["sql"]:
            ans = make_answer(question, [], sql_result)
            return _result(ans["answer"], ans["sources"], sql_result["sql"], ans["dont_know"])
        # The timetable cannot answer it, so try the documents instead.
        route = "DOCUMENTS"

    if route == "DOCUMENTS":
        chunks = search(question)
        ans = make_answer(question, chunks)
        return _result(ans["answer"], ans["sources"], None, ans["dont_know"])

    # BOTH: documents and database together.
    chunks = search(question)
    sql_result = run_sql(question)
    if sql_result["refused"] or not sql_result["sql"]:
        sql_result = None
    ans = make_answer(question, chunks, sql_result)
    sql = sql_result["sql"] if sql_result else None
    return _result(ans["answer"], ans["sources"], sql, ans["dont_know"])


def ask(question):
    """Always returns {"answer", "sources", "sql", "dont_know"}. Never crashes."""
    try:
        return _ask(question)
    except Exception:
        return _unknown()