"""Semantic similarity signal: how closely an article matches the current corpus.

Each article paragraph is embedded (same model and chunking as the corpus) and
matched to its nearest corpus chunk by cosine similarity. The article's score is
the mean of those best-match similarities: low similarity = content has drifted
from current documentation = high decay.
"""
import json

import numpy as np
from sentence_transformers import SentenceTransformer

from process_corpus import chunk_paragraphs

CHUNKS_PATH = "corpus_chunks.jsonl"
EMBEDDINGS_PATH = "corpus_embeddings.npy"
MODEL_NAME = "all-MiniLM-L6-v2"

_state = {}


def _load():
    """Load model, corpus embeddings and chunk metadata once."""
    if not _state:
        _state["model"] = SentenceTransformer(MODEL_NAME)
        _state["embeddings"] = np.load(EMBEDDINGS_PATH)
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            _state["chunks"] = [json.loads(line) for line in f]
        assert len(_state["chunks"]) == len(_state["embeddings"])
    return _state


def compute_semantic_similarity(text):
    """Return {'similarity', 'paragraphs', 'best_matches'}.

    similarity is the mean best-match cosine similarity (0-1) over the article's
    paragraphs. Returns "not_applicable" as the similarity if the text has no
    usable paragraphs.
    """
    s = _load()
    paragraphs = chunk_paragraphs(text)
    if not paragraphs:
        return {"similarity": "not_applicable", "paragraphs": 0, "best_matches": []}

    q = s["model"].encode(paragraphs, normalize_embeddings=True, show_progress_bar=False)
    sims = np.asarray(q, dtype="float32") @ s["embeddings"].T  # cosine (unit vectors)
    best_idx = sims.argmax(axis=1)
    best = sims[np.arange(len(paragraphs)), best_idx]

    matches = [
        {"paragraph": paragraphs[i][:80], "similarity": float(best[i]),
         "source": s["chunks"][best_idx[i]]["source"]}
        for i in range(len(paragraphs))
    ]
    return {"similarity": float(best.mean()), "paragraphs": len(paragraphs),
            "best_matches": matches}
