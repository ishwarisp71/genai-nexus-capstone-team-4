"""ask(question): route the question, call search and/or SQL, write the answer."""
import re

from helpdesk.answer import make_answer, DONT_KNOW_TEXT
from helpdesk.llm import generate
from helpdesk.search import search
from helpdesk.sql import run_sql

REFUSAL_TEXT = "I can't do that. I only run read-only queries."

DB_WORDS = ["which trains", "trains from", "trains between", "train number",
            "name of train", "how many trains", "how many rajdhani",
            "timetable", "stops at", "when does", "what time", "leave ",
            "arrive at", "platform"]
DOC_WORDS = ["refund", "cancel", "charge", "tatkal", "advance", "reservation",
             "gazette", "g.s.r", "circular", "rule", "fare", "how much",
             "deduct", "waitlist", "chart", "tdr", "booking limit", "ticket",
             "aadhaar", "notification"]
CHANGE_WORDS = r"\b(change|update|modify|delete|drop|insert|edit|alter|remove|erase|overwrite)\b"


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


def rule_route(question):
    """Decide the route with plain Python. Returns None when unsure."""
    q = question.lower()
    if re.search(CHANGE_WORDS, q) and re.search(r"database|table|record|\bdb\b|timetable", q):
        return "REFUSE"
    db = bool(re.search(r"\b\d{5}\b", q)) or any(w in q for w in DB_WORDS)
    doc = any(w in q for w in DOC_WORDS)
    if db and doc:
        return "BOTH"
    if db:
        return "DATABASE"
    if doc:
        return "DOCUMENTS"
    return None


def classify(question):
    """Returns DOCUMENTS, DATABASE, BOTH or REFUSE. Uses Gemini only if rules are unsure."""
    route = rule_route(question)
    if route:
        return route
    prompt = f"""You route questions for a railway help desk. Reply with ONE word only.

DOCUMENTS = about rules, refunds, cancellation charges, Tatkal, advance
            reservation period, circulars, gazette notifications, fares.
DATABASE  = about the 2016 timetable: train numbers, names, stations, times,
            which trains go from A to B, counts of trains.
BOTH      = needs the timetable AND the rules together.
REFUSE    = asks to change, add, delete or damage any data.

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
        chunks = search(question, k=8)
        ans = make_answer(question, chunks)
        return _result(ans["answer"], ans["sources"], None, ans["dont_know"])

    # BOTH: documents and database together.
    chunks = search(question, k=8)
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