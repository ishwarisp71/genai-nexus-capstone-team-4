"""Ask one question from the terminal:  python ask.py "your question" """
import json
import sys

from helpdesk.pipeline import ask

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Usage: python ask.py "your question"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(json.dumps(ask(question), indent=2, ensure_ascii=False))