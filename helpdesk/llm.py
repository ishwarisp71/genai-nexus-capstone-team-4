import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # reads GEMINI_API_KEY (and optionally GEMINI_MODEL) from .env
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")


def _call(contents, retries=5):
    """Send contents to Gemini and return the text reply.
    Waits and retries if Gemini is busy or rate-limits us."""
    wait = 2
    for attempt in range(retries):
        try:
            response = _client.models.generate_content(model=MODEL, contents=contents)
            return response.text
        except Exception as error:
            text = str(error)
            # A 404 or bad key will never fix itself, so don't retry
            if "404" in text or "API key" in text or attempt == retries - 1:
                raise
            print(f"Gemini error. Retrying in {wait}s...")
            time.sleep(wait)
            wait *= 2  # 2, 4, 8, 16 seconds


def generate(prompt, retries=5):
    """Text question in, text answer out."""
    return _call(prompt, retries)


def read_image(png_bytes, retries=5):
    """Ask Gemini to read all the text in a page image (OCR)."""
    prompt = ("Transcribe all the text on this page exactly as written, "
              "including tables, numbers, dates and rule numbers. "
              "Output only the text.")
    image = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
    return _call([image, prompt], retries)


def embed(texts, retries=5):
    """Turn a list of texts into a list of number-vectors (meaning search)."""
    vectors = []
    for i in range(0, len(texts), 50):  # 50 texts per request
        batch = texts[i:i + 50]
        wait = 2
        for attempt in range(retries):
            try:
                result = _client.models.embed_content(model=EMBED_MODEL, contents=batch)
                vectors += [e.values for e in result.embeddings]
                break
            except Exception as error:
                if "404" in str(error) or attempt == retries - 1:
                    raise
                print(f"Gemini error. Retrying in {wait}s...")
                time.sleep(wait)
                wait *= 2
        time.sleep(1)  # be gentle with the free quota
    return vectors