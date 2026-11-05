"""Tests for SQL query safety."""

import os
import sys
from pathlib import Path

os.environ.setdefault("GEMINI_API_KEY", "test-api-key")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpdesk.sql import is_safe

SAFE_QUERIES = [
    "SELECT * FROM trains",
    "SELECT train_number FROM trains",
    "SELECT * FROM trains WHERE train_number = '12002'",
    "SELECT COUNT(*) FROM trains",
    "SELECT train_number FROM trains WHERE train_number = '12002'",
    "WITH recent AS (SELECT * FROM trains) SELECT * FROM recent",
    "SELECT * FROM trains;",
    "  SELECT * FROM trains  ",
]

DANGEROUS_QUERIES = [
    "DROP TABLE trains",
    "DELETE FROM trains",
    "UPDATE trains SET train_number = '1'",
    "INSERT INTO trains VALUES ('1')",
    "ALTER TABLE trains ADD COLUMN test TEXT",
    "CREATE TABLE test (id INT)",
    "SELECT * FROM trains; DROP TABLE trains",
    "SELECT * FROM trains -- comment",
]


def main():
    passed = 0
    failed = 0

    print("\nTesting safe SQL queries:")

    for query in SAFE_QUERIES:
        result = is_safe(query)
        if result is True:
            print(f"PASS: {query}")
            passed += 1
        else:
            print(f"FAIL: {query} | Expected True, got {result}")
            failed += 1

    print("\nTesting dangerous SQL queries:")

    for query in DANGEROUS_QUERIES:
        result = is_safe(query)
        if result is False:
            print(f"PASS: {query}")
            passed += 1
        else:
            print(f"FAIL: {query} | Expected False, got {result}")
            failed += 1

    print(f"\nResults: {passed}/16 passed, {failed}/16 failed")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()