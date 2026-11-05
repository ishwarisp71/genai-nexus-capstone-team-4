import json
import os
import re

import numpy as np
from rank_bm25 import BM25Okapi

from helpdesk.llm import embed

CHUNKS_FILE = "index/chunks.json"
EMB_FILE = "index/embeddings.json"
_cache = {}
_qcache = {}  # question -> embedding, so one question is embedded only once


def tokenize(text):
    """Lowercase words and numbers. Keeps train numbers like 12430 whole."""
    return re.findall(r"[a-z0-9]+|[\u0900-\u097F]+", text.lower())


def load_chunks():
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        return json.load(f)


def build_embeddings():
    """Compute meaning-vectors for every chunk once and save them."""
    chunks = load_chunks()
    vectors = embed([c["text"] for c in chunks])
    with open(EMB_FILE, "w", encoding="utf-8") as f:
        json.dump(vectors, f)
    print(f"Saved {len(vectors)} embeddings to {EMB_FILE}")


def _load():
    if _cache:
        return _cache
    chunks = load_chunks()
    _cache["chunks"] = chunks
    _cache["bm25"] = BM25Okapi([tokenize(c["text"]) for c in chunks])
    _cache["vectors"] = None
    if os.path.exists(EMB_FILE):
        with open(EMB_FILE, encoding="utf-8") as f:
            vectors = np.array(json.load(f))
        if len(vectors) == len(chunks):
            _cache["vectors"] = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    # newer date -> bigger number between 0 and 1
    dates = sorted({c["date"] for c in chunks})
    _cache["recency"] = {d: i / max(len(dates) - 1, 1) for i, d in enumerate(dates)}
    return _cache


def _ranks(scores):
    """Turn scores into ranks: best chunk gets rank 0."""
    order = np.argsort(-np.asarray(scores))
    ranks = np.empty(len(order), dtype=int)
    ranks[order] = np.arange(len(order))
    return ranks


def _question_vector(question):
    if question not in _qcache:
        q = np.array(embed([question])[0])
        _qcache[question] = q / np.linalg.norm(q)
    return _qcache[question]


def search(question, k=5, use_embeddings=True, recency_weight=0.10):
    """Return the k best chunks: {text, doc, page, date, score}.

    use_embeddings=False -> keyword search only (BM25).
    recency_weight=0     -> no boost for newer documents.
    The defaults are the real system.
    """
    data = _load()
    chunks = data["chunks"]

    # 1) exact-word search (good for train numbers and codes like "Rule 25")
    keyword_ranks = _ranks(data["bm25"].get_scores(tokenize(question)))
    scores = 1.0 / (60 + keyword_ranks)

    # 2) meaning search (good when the wording is different)
    if use_embeddings and data["vectors"] is not None:
        try:
            q = _question_vector(question)
            scores = scores + 1.0 / (60 + _ranks(data["vectors"] @ q))
        except Exception as error:
            print(f"Meaning search skipped: {error}")

    # 3) small boost for newer documents, so the newer rule wins
    if recency_weight:
        for i, chunk in enumerate(chunks):
            scores[i] *= 1 + recency_weight * data["recency"][chunk["date"]]

    best = np.argsort(-scores)[:k]
    return [{**chunks[i], "score": float(scores[i])} for i in best]