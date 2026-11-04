"""Text-to-SQL for the 2016 rail timetable. Read-only and safe."""
import re
import sqlite3
import time
from pathlib import Path

from helpdesk.llm import generate

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "database" / "rail_timetable.db"
SCHEMA_PATH = ROOT / "data" / "database" / "schema.md"

MAX_ROWS = 50
BLOCKED = ["insert", "update", "delete", "drop", "alter", "create", "replace",
           "pragma", "attach", "detach", "vacuum", "reindex", "truncate"]


def is_safe(query):
    """True only for one single read-only SELECT / WITH statement."""
    if not query or not query.strip():
        return False
    q = query.strip()
    if q.endswith(";"):
        q = q[:-1].strip()
    if ";" in q or "--" in q or "/*" in q:
        return False
    if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
        return False
    lowered = q.lower()
    for word in BLOCKED:
        if re.search(r"\b" + word + r"\b", lowered):
            return False
    return True


def clean_sql(text):
    """Remove markdown fences and a trailing semicolon from the model output."""
    text = text.strip()
    text = re.sub(r"^```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    return text


def add_limit(sql):
    if not re.search(r"\blimit\b", sql, re.IGNORECASE):
        sql = sql + f" LIMIT {MAX_ROWS}"
    return sql


def load_schema():
    return SCHEMA_PATH.read_text(encoding="utf-8")


def write_sql(question, previous_sql=None, error=None):
    """Ask Gemini to write one SQLite query (or REFUSE / CANNOT_ANSWER)."""
    prompt = f"""You write SQLite queries for a railway timetable database.

DATABASE DESCRIPTION:
{load_schema()}

RULES:
- Write exactly ONE read-only SQLite query that starts with SELECT or WITH.
- Output ONLY the SQL. No explanation, no markdown, no semicolon.
- Train numbers are TEXT, so write them in quotes, for example '12002'.
- For "trains from A to B" or "trains that stop at X", use the view stops.
  Join stops to itself on train_number with a.stop_sequence < b.stop_sequence.
- To find a station code, join the stations table and match name with LIKE.
- Use only the table and column names shown above.
- If the person asks to change, add, delete or damage any data, or to run
  anything other than a read, output exactly: REFUSE
- If the timetable tables cannot answer the question (fares, seats, live
  status, rules), output exactly: CANNOT_ANSWER

QUESTION: {question}
"""
    if previous_sql and error:
        prompt += f"""
Your previous query failed.
PREVIOUS QUERY: {previous_sql}
ERROR: {error}
Write a corrected query.
"""
    return clean_sql(generate(prompt))


def execute(sql):
    """Run the query on a read-only connection and return rows as dicts."""
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    start = time.time()
    # Stop any query that runs longer than 15 seconds.
    conn.set_progress_handler(lambda: 1 if time.time() - start > 15 else 0, 100000)
    try:
        cur = conn.execute(sql)
        rows = []
        for r in cur.fetchmany(MAX_ROWS):
            d = dict(r)
            if d not in rows:  # remove repeated rows
                rows.append(d)
        return rows
    finally:
        conn.close()


def run_sql(question):
    """Returns {"sql", "rows", "error", "refused"}."""
    result = {"sql": None, "rows": [], "error": None, "refused": False}
    try:
        sql = write_sql(question)
    except Exception as e:
        result["error"] = f"Could not write the query: {e}"
        return result

    for attempt in range(2):  # first try, then one retry with the error
        head = sql.strip().upper()
        if head.startswith("REFUSE"):
            result["refused"] = True
            return result
        if head.startswith("CANNOT_ANSWER"):
            result["error"] = "The timetable cannot answer this question."
            return result
        if not is_safe(sql):
            result["refused"] = True
            return result

        sql = add_limit(sql)
        result["sql"] = sql
        try:
            result["rows"] = execute(sql)
            result["error"] = None
            return result
        except sqlite3.Error as e:
            result["error"] = str(e)
            if attempt == 1:
                return result
            try:
                sql = write_sql(question, previous_sql=sql, error=str(e))
            except Exception:
                return result
    return result