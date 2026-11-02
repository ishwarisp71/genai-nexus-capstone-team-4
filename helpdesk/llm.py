import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()  # reads GEMINI_API_KEY (and optionally GEMINI_MODEL) from .env
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def generate(prompt, retries=5):
    """Send a prompt to Gemini and return the text reply.
    Waits and retries if Gemini is busy or rate-limits us."""
    wait = 2
    for attempt in range(retries):
        try:
            response = _client.models.generate_content(model=MODEL, contents=prompt)
            return response.text
        except Exception as error:
            text = str(error)
            # A 404 or bad key will never fix itself, so don't waste time retrying
            if "404" in text or "API key" in text or attempt == retries - 1:
                raise
            print(f"Gemini error. Retrying in {wait}s...")
            time.sleep(wait)
            wait *= 2  