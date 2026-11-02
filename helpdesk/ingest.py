import glob
import json
import os
import re

import pymupdf
from bs4 import BeautifulSoup

from helpdesk.llm import read_image

DOCS_DIR = "data/documents"
CACHE_FILE = "index/ocr_cache.json"
MIN_TEXT = 50          # a page with fewer characters than this is treated as a scan
CHUNK_SIZE = 1200      # characters per chunk

# Date of each document, so the NEWER one wins when they disagree.
# The last two are still guesses: check them in data/SOURCES.md.
DOC_DATES = {
    "indianrail_refund_rules_2015": "2015-11-12",
    "rb_cc10_2024_advance_reservation": "2024-10-16",
    "rb_cc08_2025_tatkal": "2025-06-10",
    "rb_cc10_2025_reservation_charts": "2025-07-02",
    "rb_cc08_2026_vande_bharat_sleeper_refund": "2026-01-19",
    "irctc_refund_rules_jan2026": "2026-01-19",
    "pib_2026-03-24": "2026-03-24",
}


def get_date(filename):
    for key, date in DOC_DATES.items():
        if filename.startswith(key):
            return date
    return "unknown"


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs("index", exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def split_text(text, size=CHUNK_SIZE):
    """Cut long text into chunks at paragraph or line breaks."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks, current = [], ""
    for part in re.split(r"(?<=\n)", text):
        if len(current) + len(part) > size and current:
            chunks.append(current.strip())
            current = ""
        current += part
    if current.strip():
        chunks.append(current.strip())
    return chunks


def read_pdf(path, cache):
    filename = os.path.basename(path)
    date = get_date(filename)
    chunks = []
    doc = pymupdf.open(path)
    for number, page in enumerate(doc, start=1):
        text = page.get_text()
        if len(text.strip()) < MIN_TEXT:  # scanned page -> OCR
            key = f"{filename}:{number}"
            if key not in cache:
                print(f"OCR {filename} page {number} ...")
                png = page.get_pixmap(dpi=200).tobytes("png")
                cache[key] = read_image(png)
                save_cache(cache)  # save after every page so work is never lost
            text = cache[key]
            if "appears to be blank" in text or len(text.strip()) < MIN_TEXT:
                continue  # blank scan, nothing to index
        for piece in split_text(text):
            chunks.append({"text": piece, "doc": filename, "page": number, "date": date})
    return chunks


def read_html(path):
    filename = os.path.basename(path)
    date = get_date(filename)
    with open(path, encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup(["script", "style", "iframe", "svg"]):
        tag.decompose()
    body = soup.find(id="pibReleaseBody") or soup

    chunks = []
    # Keep every table row whole, so a rule and its numbers stay together
    for row in body.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        line = " | ".join(c for c in cells if c)
        if len(line) > 20:
            chunks.append({"text": line, "doc": filename, "page": None, "date": date})
    for table in body.find_all("table"):
        table.decompose()
    for piece in split_text(body.get_text("\n", strip=True)):
        chunks.append({"text": piece, "doc": filename, "page": None, "date": date})
    return chunks


def build_chunks():
    """Read all 7 documents and return a list of chunks."""
    cache = load_cache()
    chunks = []
    for path in sorted(glob.glob(f"{DOCS_DIR}/*")):
        if path.lower().endswith(".pdf"):
            chunks += read_pdf(path, cache)
        elif path.lower().endswith((".html", ".htm")):
            chunks += read_html(path)
    return chunks