# Railway Passenger Help Desk (RAG + text-to-SQL)

GenAI Nexus, Cohort 1, Module 2 capstone. Team 4 (Griffin).

A terminal help desk for railway passengers. It answers from official rule
documents and a 2016 train timetable database, shows its sources, uses the
newest rule when old and new rules conflict, refuses to change data, and says
"I don't know" when the pack does not cover the question.

`ask(question)` always returns:

```json
{"answer": "plain-words reply",
 "sources": [{"doc": "irctc_refund_rules_jan2026.pdf", "page": 3}],
 "sql": "SELECT ... or null",
 "dont_know": false}
```

`page` is null for HTML files. `dont_know` is true when it declines.

## How it works